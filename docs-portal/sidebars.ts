import type { SidebarsConfig } from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'index',
    {
      type: 'category',
      label: 'Installation',
      items: ['installation/index', 'installation/production-setup', 'installation/update'],
    },
    {
      type: 'category',
      label: 'Configuration',
      items: ['configuration/index'],
    },
    {
      type: 'category',
      label: 'User Guide',
      items: [
        'user-guide/prompt-management',
        'user-guide/categories',
        'user-guide/tags',
        'user-guide/placeholders',
        'user-guide/search',
        'user-guide/pagination',
        'user-guide/import-export',
        'user-guide/sharing',
        'user-guide/skills',
        'user-guide/versioning',
        'user-guide/backups',
        'user-guide/two-factor-auth',
      ],
    },
    {
      type: 'category',
      label: 'Developer / API',
      link: { type: 'doc', id: 'developer-api/index' },
      items: ['developer-api/getting-started', 'developer-api/reference'],
    },
    {
      type: 'category',
      label: 'Troubleshooting',
      items: ['troubleshooting/index'],
    },
    {
      type: 'category',
      label: 'Release Notes',
      items: ['release-notes/index'],
    },
  ],
};

export default sidebars;
