"""Typed, local-only decision support.

The engine is deliberately not a gate.  It consumes bounded metadata already
computed by Hub components and returns a typed recommendation or an explicit
abstention.  It never executes a command, changes a lifecycle result, or
writes to a connected project.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .config import STORAGE_DIR as HUB_STORAGE_DIR, ProjectConfig


ENGINE_VERSION = "1"
REGISTRY_VERSION = "1"
POLICY_VERSION = "1"
STORAGE_DIR = HUB_STORAGE_DIR / "decision-engine"
MAX_FEATURES_BYTES = 8_192
MAX_CACHE_FILES = 200
MAX_LOCAL_RESPONSE_BYTES = 16_384
VALID_MODES = {"shadow", "advisory", "auto"}
VALID_STATUSES = {"ok", "uncertain", "unavailable", "timeout", "invalid_output", "unsupported", "stale"}
PROJECT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


class DecisionValidationError(ValueError):
    """Raised before any provider receives an invalid request."""


@dataclass(frozen=True)
class Feature:
    kind: str
    required: bool = True
    values: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class DecisionSpec:
    decision_id: str
    value_type: str
    features: Mapping[str, Feature]
    risk_class: str
    allowed_values: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    providers: tuple[str, ...] = ("rules", "local")
    modes: tuple[str, ...] = ("shadow", "advisory")
    schema_version: str = "1"


REGISTRY: dict[str, DecisionSpec] = {
    "context.docs_ready": DecisionSpec("context.docs_ready", "boolean", {
        "docs_ready": Feature("boolean"),
    }, "low"),
    "patch.risk": DecisionSpec("patch.risk", "score", {
        "risk_level": Feature("choice", values=("low", "medium", "high")),
        "surface_count": Feature("integer", minimum=0, maximum=64),
        "changed_files_count": Feature("integer", minimum=0, maximum=10000),
    }, "medium", minimum=0, maximum=100),
    "patch.security_review_depth": DecisionSpec("patch.security_review_depth", "choice", {
        "risk_level": Feature("choice", values=("low", "medium", "high")),
        "has_security_surface": Feature("boolean"),
        "docs_only": Feature("boolean"),
    }, "high", allowed_values=("minimal", "normal", "extended")),
    "context.primary_sources": DecisionSpec("context.primary_sources", "choice", {
        "docs_ready": Feature("boolean"), "has_patch": Feature("boolean"),
        "has_skills": Feature("boolean"), "has_history": Feature("boolean"),
    }, "low", allowed_values=("docs", "code", "decisions", "skills", "history")),
    "skill.candidate_priority": DecisionSpec("skill.candidate_priority", "score", {
        "candidate_score": Feature("number", minimum=0, maximum=1),
        "validation_errors": Feature("integer", minimum=0, maximum=1000),
    }, "low", minimum=0, maximum=100),
    "patch.documentation_impact": DecisionSpec("patch.documentation_impact", "choice", {
        "docs_only": Feature("boolean"), "changed_files_count": Feature("integer", minimum=0, maximum=10000),
        "has_runtime_surface": Feature("boolean"),
    }, "medium", allowed_values=("none", "likely", "required_review")),
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _safe_project_id(value: str) -> str:
    if not PROJECT_RE.fullmatch(value):
        raise DecisionValidationError("project id must be a bounded safe identifier")
    return value


@dataclass(frozen=True)
class EngineSettings:
    enabled: bool = True
    provider: str = "rules"
    mode: str = "shadow"
    auto_enabled: bool = False
    local_endpoint: str | None = None
    timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.provider not in {"rules", "local"}:
            raise DecisionValidationError("provider must be rules or local")
        if self.mode not in VALID_MODES:
            raise DecisionValidationError("mode must be shadow, advisory, or auto")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 10:
            raise DecisionValidationError("timeout_seconds must be within 0..10")


def default_settings() -> EngineSettings:
    """The only default: offline rules in non-impacting shadow mode."""
    return EngineSettings()


def _validate_features(spec: DecisionSpec, features: Any) -> dict[str, Any]:
    if not isinstance(features, dict) or set(features) != set(spec.features):
        raise DecisionValidationError("features must exactly match the registered feature schema")
    if len(canonical_json(features)) > MAX_FEATURES_BYTES:
        raise DecisionValidationError("features exceed the bounded metadata limit")
    normalized: dict[str, Any] = {}
    for name, definition in spec.features.items():
        value = features[name]
        if definition.kind == "boolean":
            if type(value) is not bool:
                raise DecisionValidationError(f"feature {name} must be boolean")
        elif definition.kind == "integer":
            if type(value) is not int:
                raise DecisionValidationError(f"feature {name} must be integer")
        elif definition.kind == "number":
            if type(value) not in {int, float} or isinstance(value, bool) or not math.isfinite(float(value)):
                raise DecisionValidationError(f"feature {name} must be a finite number")
        elif definition.kind == "choice":
            if type(value) is not str or value not in definition.values:
                raise DecisionValidationError(f"feature {name} must be an allowed choice")
        else:
            raise DecisionValidationError("unsupported feature type")
        if definition.minimum is not None and float(value) < definition.minimum:
            raise DecisionValidationError(f"feature {name} is below the allowed range")
        if definition.maximum is not None and float(value) > definition.maximum:
            raise DecisionValidationError(f"feature {name} is above the allowed range")
        normalized[name] = value
    return normalized


def _rules(spec: DecisionSpec, features: dict[str, Any]) -> tuple[Any | None, list[str], str]:
    if spec.decision_id == "context.docs_ready":
        return features["docs_ready"], ["documentation_status"], "none"
    if spec.decision_id == "patch.risk":
        score = {"low": 15, "medium": 45, "high": 75}[features["risk_level"]]
        score = min(100, score + min(15, features["surface_count"] * 2) + min(10, features["changed_files_count"] // 20))
        return score, ["surface_heuristic", "uncalibrated_rules"], "uncalibrated"
    if spec.decision_id == "patch.security_review_depth":
        if features["risk_level"] == "high" or features["has_security_surface"]:
            return "extended", ["security_surface", "minimum_not_lowered"], "none"
        if features["docs_only"]:
            return "minimal", ["docs_only"], "none"
        return "normal", ["deterministic_minimum"], "none"
    if spec.decision_id == "context.primary_sources":
        if features["has_patch"]:
            return "code", ["working_patch"], "none"
        if not features["docs_ready"]:
            return "docs", ["docs_unavailable"], "none"
        if features["has_skills"]:
            return "skills", ["skill_catalog_available"], "none"
        if features["has_history"]:
            return "history", ["history_available"], "none"
        return "decisions", ["stable_default"], "none"
    if spec.decision_id == "skill.candidate_priority":
        if features["validation_errors"]:
            return 0, ["validation_errors", "uncalibrated_rules"], "uncalibrated"
        return round(float(features["candidate_score"]) * 100), ["existing_skill_score", "uncalibrated_rules"], "uncalibrated"
    if spec.decision_id == "patch.documentation_impact":
        if features["has_runtime_surface"]:
            return "required_review", ["runtime_surface"], "none"
        if features["docs_only"]:
            return "none", ["docs_only"], "none"
        return "likely", ["non_docs_change"], "none"
    return None, ["unsupported_decision"], "none"


def _validate_value(spec: DecisionSpec, value: Any) -> Any:
    if spec.value_type == "boolean" and type(value) is not bool:
        raise DecisionValidationError("provider boolean output is invalid")
    if spec.value_type == "choice" and (type(value) is not str or value not in spec.allowed_values):
        raise DecisionValidationError("provider choice output is invalid")
    if spec.value_type == "score":
        if type(value) not in {int, float} or isinstance(value, bool) or not math.isfinite(float(value)):
            raise DecisionValidationError("provider score output is invalid")
        if float(value) < float(spec.minimum) or float(value) > float(spec.maximum):
            raise DecisionValidationError("provider score is outside the registered range")
    return value


class LocalHttpProvider:
    """Optional, proxy-free loopback adapter.  It is never started by Hub."""

    def __init__(self, endpoint: str | None, timeout_seconds: float) -> None:
        self.endpoint, self.timeout_seconds = endpoint, timeout_seconds

    def evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.endpoint:
            return {"status": "unavailable", "reason_codes": ["local_endpoint_missing"]}
        parsed = urllib.parse.urlparse(self.endpoint)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"} or parsed.username or parsed.password:
            return {"status": "unavailable", "reason_codes": ["local_endpoint_not_loopback"]}
        try:
            socket.inet_pton(socket.AF_INET6 if parsed.hostname == "::1" else socket.AF_INET, parsed.hostname)
        except OSError:
            return {"status": "unavailable", "reason_codes": ["local_endpoint_invalid"]}
        request = urllib.request.Request(parsed.geturl(), data=canonical_json(payload), method="POST", headers={"Content-Type": "application/json"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        try:
            with opener.open(request, timeout=self.timeout_seconds) as response:
                if response.geturl() != parsed.geturl():
                    return {"status": "unavailable", "reason_codes": ["redirect_blocked"]}
                raw = response.read(MAX_LOCAL_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError:
            return {"status": "unavailable", "reason_codes": ["local_http_error"]}
        except TimeoutError:
            return {"status": "timeout", "reason_codes": ["local_timeout"]}
        except (OSError, urllib.error.URLError):
            return {"status": "unavailable", "reason_codes": ["local_unavailable"]}
        if len(raw) > MAX_LOCAL_RESPONSE_BYTES:
            return {"status": "invalid_output", "reason_codes": ["local_response_too_large"]}
        try:
            result = json.loads(raw)
        except ValueError:
            return {"status": "invalid_output", "reason_codes": ["local_response_invalid_json"]}
        return result if isinstance(result, dict) else {"status": "invalid_output", "reason_codes": ["local_response_not_object"]}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


class DecisionEngine:
    def __init__(self, config: ProjectConfig, settings: EngineSettings | None = None, storage_dir: Path = STORAGE_DIR) -> None:
        self.config, self.settings, self.storage_dir = config, settings or default_settings(), storage_dir
        _safe_project_id(config.project)

    def status(self) -> dict[str, Any]:
        return {"engine_version": ENGINE_VERSION, "enabled": self.settings.enabled, "provider": self.settings.provider,
                "mode": self.settings.mode, "auto_enabled": self.settings.auto_enabled,
                "supported_decisions": sorted(REGISTRY), "optional_backend": "configured" if self.settings.local_endpoint else "not_configured",
                "auto_enabled_count": 0}

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        started = time.monotonic()
        try:
            result = self._evaluate(request)
        except DecisionValidationError as exc:
            result = self._result(None, "unsupported", None, ["invalid_request"], None, None, str(exc))
        result["latency_ms"] = round((time.monotonic() - started) * 1000)
        self._record_metric(result)
        return result

    def _evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict) or set(request) - {"version", "project", "namespace", "decision_id", "features", "mode", "fingerprint", "scope", "base", "choices"}:
            raise DecisionValidationError("request has unknown fields")
        if request.get("version") != 1 or request.get("project") != self.config.project or request.get("namespace") != self.config.namespace:
            raise DecisionValidationError("request identity does not match the trusted project scope")
        decision_id = request.get("decision_id")
        if not isinstance(decision_id, str) or decision_id not in REGISTRY:
            raise DecisionValidationError("decision_id is not registered")
        spec = REGISTRY[decision_id]
        features = _validate_features(spec, request.get("features"))
        mode = request.get("mode", self.settings.mode)
        if mode not in VALID_MODES or mode not in spec.modes:
            return self._result(spec, "unsupported", None, ["mode_not_supported"], mode, None)
        if mode == "auto" or self.settings.auto_enabled:
            return self._result(spec, "unsupported", None, ["auto_not_enabled"], mode, None)
        fingerprint = request.get("fingerprint")
        if fingerprint is not None and (type(fingerprint) is not str or not re.fullmatch(r"[a-f0-9]{64}", fingerprint)):
            raise DecisionValidationError("fingerprint must be a sha256 digest")
        if decision_id.startswith("patch.") and request.get("scope") is not None:
            from .project_lifecycle import patch_fingerprint
            try:
                current = patch_fingerprint(self.config, scope=str(request["scope"]), base=request.get("base")).get("fingerprint")
            except Exception:  # fingerprint is a hard dependency for patch decisions
                return self._result(spec, "unavailable", None, ["patch_fingerprint_unavailable"], mode, fingerprint)
            if fingerprint != current:
                return self._result(spec, "stale", None, ["patch_fingerprint_stale"], mode, fingerprint)
        if not self.settings.enabled:
            return self._result(spec, "unavailable", None, ["engine_disabled"], mode, fingerprint)
        cache_key = _hash({"project": self.config.project, "namespace": self.config.namespace, "decision": decision_id,
                           "schema": spec.schema_version, "policy": POLICY_VERSION, "features": features, "fingerprint": fingerprint,
                           "scope": request.get("scope"), "base": request.get("base"), "provider": self.settings.provider,
                           "mode": mode, "engine": ENGINE_VERSION})
        cached = self._read_cache(cache_key)
        if cached:
            return {**cached, "cache": "hit"}
        if self.settings.provider == "rules":
            value, reasons, confidence_kind = _rules(spec, features)
            result = self._result(spec, "ok", _validate_value(spec, value), reasons, mode, fingerprint, confidence_kind=confidence_kind)
        else:
            remote = LocalHttpProvider(self.settings.local_endpoint, self.settings.timeout_seconds).evaluate({"version": 1, "decision_id": decision_id, "features": features})
            status = str(remote.get("status", "invalid_output"))
            if status not in VALID_STATUSES:
                status = "invalid_output"
            if status == "ok":
                try:
                    value = _validate_value(spec, remote.get("value"))
                except DecisionValidationError:
                    return self._result(spec, "invalid_output", None, ["local_value_invalid"], mode, fingerprint)
                result = self._result(spec, "ok", value, ["local_adapter"], mode, fingerprint, provider_version=str(remote.get("model_version", "unknown")))
            else:
                result = self._result(spec, status, None, list(remote.get("reason_codes", ["local_failed"]))[:8], mode, fingerprint)
        self._write_cache(cache_key, result)
        return {**result, "cache": "miss"}

    def _result(self, spec: DecisionSpec | None, status: str, value: Any, reasons: list[str], mode: str | None, fingerprint: str | None,
                detail: str | None = None, confidence_kind: str = "none", provider_version: str | None = None) -> dict[str, Any]:
        return {"status": status, "decision_id": spec.decision_id if spec else None, "value_type": spec.value_type if spec else None,
                "value": value if status == "ok" else None, "reason_codes": sorted({str(item)[:80] for item in reasons})[:8],
                "evidence_refs": [], "provider": self.settings.provider, "provider_version": provider_version or ENGINE_VERSION,
                "decision_schema_version": spec.schema_version if spec else None, "policy_version": POLICY_VERSION,
                "actual_mode": mode, "escalation_required": status != "ok" or mode == "shadow",
                "confidence": None, "confidence_kind": confidence_kind, "fingerprint": fingerprint,
                "detail": detail if detail and status == "unsupported" else None}

    def _project_dir(self) -> Path:
        return self.storage_dir / _safe_project_id(self.config.project)

    def _read_cache(self, key: str) -> dict[str, Any] | None:
        path = self._project_dir() / "cache" / f"{key}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict) or data.get("cache_key") != key:
            return None
        data.pop("cache_key", None)
        return data

    def _write_cache(self, key: str, result: dict[str, Any]) -> None:
        if result.get("status") != "ok":
            return
        directory = self._project_dir() / "cache"
        directory.mkdir(parents=True, exist_ok=True)
        payload = {key: value for key, value in result.items() if key not in {"latency_ms", "cache"}}
        payload["cache_key"] = key
        target = directory / f"{key}.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(canonical_json(payload))
        temporary.replace(target)
        for old in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime)[:-MAX_CACHE_FILES]:
            old.unlink(missing_ok=True)

    def _record_metric(self, result: dict[str, Any]) -> None:
        directory = self._project_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "metrics.json"
        try:
            metrics = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            metrics = {"schema_version": 1, "counts": {}, "latencies_ms": [], "escalations": 0}
        key = f"{result.get('decision_id') or 'invalid'}:{result['status']}"
        metrics["counts"][key] = int(metrics["counts"].get(key, 0)) + 1
        metrics["escalations"] += int(bool(result.get("escalation_required")))
        metrics["latencies_ms"] = (metrics.get("latencies_ms", []) + [int(result.get("latency_ms", 0))])[-200:]
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(canonical_json(metrics))
        tmp.replace(path)


def decision_status(config: ProjectConfig, settings: EngineSettings | None = None) -> dict[str, Any]:
    return DecisionEngine(config, settings).status()
