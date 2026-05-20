import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'http://localhost:4321',
  integrations: [
    starlight({
      title: 'AI Docs Hub',
      description: 'Local docs-as-code, llms.txt, RAG, and MCP infrastructure for project documentation.',
      components: {
        MarkdownContent: './src/components/MarkdownContent.astro'
      },
      sidebar: [
        {
          label: 'Hub',
          items: [
            { label: 'Статус', link: '/status/' },
            { label: 'Обзор', slug: 'hub/overview' },
            { label: 'Архитектура', slug: 'hub/architecture' },
            { label: 'Автономная настройка', slug: 'hub/autonomous-setup' },
            { label: 'Использование', slug: 'hub/usage' },
            { label: 'Справочник команд', slug: 'hub/command-reference' },
            { label: 'Правила агентов', slug: 'hub/agent-rules' }
          ]
        },
        {
          label: 'Operations',
          items: [
            { label: 'Локальный runtime', slug: 'hub/local-runtime' },
            { label: 'Наблюдаемость runtime', slug: 'hub/runtime-observability' },
            { label: 'GUI dashboard', slug: 'hub/gui-dashboard' },
            { label: 'macOS menu bar', slug: 'hub/macos-menu-bar' }
          ]
        },
        {
          label: 'Standards',
          items: [
            { label: 'Documentation', slug: 'standards/documentation' },
            { label: 'Project Config', slug: 'standards/project-config' },
            { label: 'Source Discovery', slug: 'standards/source-discovery' },
            { label: 'llms.txt', slug: 'standards/llms-txt' },
            { label: 'RAG Policy', slug: 'standards/rag-policy' },
            { label: 'MCP Policy', slug: 'standards/mcp-policy' },
            { label: 'Runtime Status', slug: 'standards/runtime-status' },
            { label: 'Status Diagnostics', slug: 'standards/status-diagnostics' },
            { label: 'Scaffold', slug: 'standards/scaffold' },
            { label: 'Generated Artifacts', slug: 'standards/generated-artifacts' },
            { label: 'Security', slug: 'standards/security' }
          ]
        },
        {
          label: 'Projects',
          autogenerate: { directory: 'projects' }
        }
      ]
    })
  ]
});
