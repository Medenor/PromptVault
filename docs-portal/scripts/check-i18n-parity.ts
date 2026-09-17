import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import matter from 'gray-matter';

const DOCS_ROOT = join(__dirname, '..', 'docs');
const LOCALES = ['fr', 'de', 'es'] as const;
type Locale = (typeof LOCALES)[number];

function localeRoot(locale: Locale): string {
  return join(__dirname, '..', 'i18n', locale, 'docusaurus-plugin-content-docs', 'current');
}

interface PageInfo {
  relPath: string;
  headingCount: number;
  translationExempt: boolean;
}

function walkMarkdownFiles(root: string): string[] {
  if (!existsSync(root)) return [];
  const out: string[] = [];
  for (const entry of readdirSync(root)) {
    if (entry.startsWith('_')) continue;
    const full = join(root, entry);
    if (statSync(full).isDirectory()) {
      out.push(...walkMarkdownFiles(full));
    } else if (entry.endsWith('.md')) {
      out.push(full);
    }
  }
  return out;
}

function countHeadings(body: string): number {
  return body.split('\n').filter((line) => /^(##|###)\s/.test(line)).length;
}

function parsePage(absPath: string, root: string): PageInfo {
  const raw = readFileSync(absPath, 'utf-8');
  const { data, content } = matter(raw);
  let translationExempt = false;
  if ('translation_exempt' in data) {
    if (typeof data.translation_exempt === 'boolean') {
      translationExempt = data.translation_exempt;
    } else {
      console.warn(
        `WARNING: ${relative(process.cwd(), absPath)} has non-boolean translation_exempt (${JSON.stringify(
          data.translation_exempt,
        )}) — treating as false`,
      );
    }
  }
  return {
    relPath: relative(root, absPath).split('\\').join('/'),
    headingCount: countHeadings(content),
    translationExempt,
  };
}

interface Finding {
  locale: Locale;
  kind: 'missing-page' | 'heading-count-mismatch';
  pagePath: string;
  expected: number | null;
  actual: number | null;
}

function main(): void {
  const englishFiles = walkMarkdownFiles(DOCS_ROOT);
  const englishPages = englishFiles.map((f) => parsePage(f, DOCS_ROOT));
  const enforcedPages = englishPages.filter((p) => !p.translationExempt);
  const exemptedCount = englishPages.length - enforcedPages.length;

  const findings: Finding[] = [];

  for (const locale of LOCALES) {
    const root = localeRoot(locale);
    for (const page of enforcedPages) {
      const translatedAbsPath = join(root, page.relPath);
      if (!existsSync(translatedAbsPath)) {
        findings.push({
          locale,
          kind: 'missing-page',
          pagePath: `docs/${page.relPath}`,
          expected: null,
          actual: null,
        });
        continue;
      }
      const translated = parsePage(translatedAbsPath, root);
      if (translated.headingCount !== page.headingCount) {
        findings.push({
          locale,
          kind: 'heading-count-mismatch',
          pagePath: `docs/${page.relPath}`,
          expected: page.headingCount,
          actual: translated.headingCount,
        });
      }
    }
  }

  if (findings.length === 0) {
    console.log(
      `i18n parity check passed: ${enforcedPages.length} pages × ${LOCALES.length} locales, ${exemptedCount} exemptions skipped`,
    );
    process.exit(0);
  }

  for (const finding of findings) {
    if (finding.kind === 'missing-page') {
      console.log(`[${finding.locale}] MISSING: ${finding.pagePath} has no i18n/${finding.locale} counterpart`);
    } else {
      console.log(
        `[${finding.locale}] HEADING_MISMATCH: ${finding.pagePath} — en has ${finding.expected} sections (##/###), ${finding.locale} has ${finding.actual}`,
      );
    }
  }

  const affectedLocales = new Set(findings.map((f) => f.locale)).size;
  console.log(`i18n parity check FAILED: ${findings.length} findings across ${affectedLocales} locales`);
  process.exit(1);
}

main();
