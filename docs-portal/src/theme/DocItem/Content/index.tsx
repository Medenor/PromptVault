import React, {type ReactNode} from 'react';
import Content from '@theme-original/DocItem/Content';
import type ContentType from '@theme/DocItem/Content';
import type {WrapperProps} from '@docusaurus/types';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import Translate from '@docusaurus/Translate';

type Props = WrapperProps<typeof ContentType>;

/**
 * Docusaurus has no built-in notice for this: when a doc is missing in the
 * current locale, the i18n plugin silently falls back to the default-locale
 * (English) source file instead of 404ing. The only observable trace of that
 * fallback is `metadata.source` still pointing at `@site/docs/...` (the
 * English tree) rather than `@site/i18n/<locale>/...` (FR-006).
 */
function isUntranslatedFallback(source: string, locale: string): boolean {
  return !source.includes(`/i18n/${locale}/`);
}

export default function ContentWrapper(props: Props): ReactNode {
  const {
    i18n: {currentLocale, defaultLocale},
  } = useDocusaurusContext();
  const {metadata} = useDoc();

  const showBanner =
    currentLocale !== defaultLocale &&
    isUntranslatedFallback(metadata.source, currentLocale);

  return (
    <>
      {showBanner && (
        <div className="alert alert--warning margin-bottom--md" role="alert">
          <Translate id="theme.docs.untranslatedBanner">
            This page has not been translated yet. You are viewing the
            English version.
          </Translate>
        </div>
      )}
      <Content {...props} />
    </>
  );
}
