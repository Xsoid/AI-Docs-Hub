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
            { label: 'Overview', slug: 'hub/overview' },
            { label: 'Architecture', slug: 'hub/architecture' },
            { label: 'Usage', slug: 'hub/usage' },
            { label: 'Agent Rules', slug: 'hub/agent-rules' }
          ]
        },
        {
          label: 'Standards',
          items: [
            { label: 'Documentation', slug: 'standards/documentation' },
            { label: 'llms.txt', slug: 'standards/llms-txt' },
            { label: 'RAG Policy', slug: 'standards/rag-policy' },
            { label: 'MCP Policy', slug: 'standards/mcp-policy' }
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
