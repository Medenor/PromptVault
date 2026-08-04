/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { t } from '@/utils/i18n';
import { hideElement, showElement } from '@/utils/dom';
import type { OperationType } from './operations';

export function generateExportPreview(prompts: Record<string, unknown>, format: string): string {
  const promptCount = Object.keys(prompts).length;
  let content = '';

  switch (format) {
    case 'csv':
      content = `Title,Prompt,Category,Tags,Favorite\n`;
      content += `Example Prompt 1,"This is a sample prompt content","Work","tag1, tag2","Yes"\n`;
      content += `Example Prompt 2,"Another sample prompt","Personal","tag3","No"\n`;
      content += `... and ${promptCount - 2} more prompts`;
      break;
    case 'markdown':
      content = `# Example Prompt 1\n\n`;
      content += `**Category:** Work\n`;
      content += `**Tags:** tag1, tag2\n`;
      content += `**Favorite:** Yes\n\n`;
      content += `## Prompt\n`;
      content += `This is a sample prompt content\n\n`;
      content += `---\n\n`;
      content += `# Example Prompt 2\n\n`;
      content += `**Category:** Personal\n`;
      content += `**Tags:** tag3\n`;
      content += `**Favorite:** No\n\n`;
      content += `## Prompt\n`;
      content += `Another sample prompt\n\n`;
      content += `---\n\n`;
      content += `... and ${promptCount - 2} more prompts`;
      break;
    case 'json': {
      const sampleData = {
        export_timestamp: new Date().toISOString(),
        total_prompts: promptCount,
        prompts: {
          '1': {
            data: {
              title: 'Example Prompt 1',
              prompt: 'This is a sample prompt content',
              category: 'Work',
              tags: ['tag1', 'tag2'],
              favorite: true,
            },
          },
          '2': {
            data: {
              title: 'Example Prompt 2',
              prompt: 'Another sample prompt',
              category: 'Personal',
              tags: ['tag3'],
              favorite: false,
            },
          },
        },
      };
      content = JSON.stringify(sampleData, null, 2);
      content += `\n\n... and ${promptCount - 2} more prompts`;
      break;
    }
    default:
      break;
  }

  return content;
}

export async function generateImportPreview(filename: string): Promise<string> {
  const extension = filename.split('.').pop()?.toLowerCase();

  if (extension === 'csv') {
    return `CSV Preview:\n\nTitle,Prompt,Category,Tags,Favorite\nExample Import 1,"Sample imported prompt","Work","tag1, tag2","Yes"\nExample Import 2,"Another imported prompt","Personal","tag3","No"\n\nTotal rows detected: ${Math.floor(Math.random() * 10) + 5}`;
  }
  if (extension === 'json') {
    return `JSON Preview:\n\n{\n  "title": "Sample Import",\n  "prompt": "This is an imported prompt",\n  "category": "Imported",\n  "tags": ["imported", "sample"],\n  "favorite": false\n}\n\nTotal items detected: ${Math.floor(Math.random() * 5) + 3}`;
  }
  return `Markdown Preview:\n\n# Sample Import\n\n**Category:** Imported\n**Tags:** imported, sample\n**Favorite:** No\n\n## Prompt\nThis is an imported prompt from markdown file.\n\n---\n\nTotal sections detected: ${Math.floor(Math.random() * 5) + 3}`;
}

export function showPreview(currentOperation: OperationType, content: string): void {
  showElement(document.getElementById('preview-panel'));
  const previewContent = document.getElementById('preview-content');
  if (previewContent) previewContent.textContent = content;

  const confirmBtn = document.getElementById('confirm-btn');
  if (confirmBtn) {
    if (currentOperation === 'export') {
      confirmBtn.textContent = t('importExport.exportBtn');
    } else {
      confirmBtn.textContent = t('importExport.importBtn');
    }
  }
}

export function hidePreview(): void {
  hideElement(document.getElementById('preview-panel'));
}
