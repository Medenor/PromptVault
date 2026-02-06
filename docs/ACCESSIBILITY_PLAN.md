# Plan d'Accessibilité WCAG 2.1 AA - PromptVault

## Vue d'ensemble

Ce plan détaille les étapes nécessaires pour atteindre la conformité WCAG 2.1 AA pour PromptVault. Le projet utilise FastAPI (Python) pour le backend, TypeScript/Vite pour le frontend, et Tailwind CSS v4 pour le stylisme.

**Complexité technique:** Moyenne | **Effort estimé:** 3 semaines | **Valeur utilisateur:** Haute

## Statut d'avancement (mise à jour: 2026-02-06)

### Légende

- `[x]` Implémenté
- `[~]` Partiellement implémenté / en cours
- `[ ]` Non implémenté

### Tâches implémentées

- `[x] T-ACC001` Configurer axe-core pour les tests navigateur (Playwright + `@axe-core/playwright`)
- `[x] T-ACC002` Lighthouse CI dans pipeline (workflow Forgejo + seuil accessibilité >= 95)
- `[x] T-ACC003` Créer un script de test d'accessibilité local (`scripts/accessibility_test.py`)
- `[x] T-ACC004` Documenter les outils d'accessibilité (`docs/ACCESSIBILITY_TESTING.md`)
- `[x] T-ACC011` Créer le lien "Aller au contenu principal" (skip link) sur les pages principales/templates actifs
- `[x] T-ACC013` Indicateurs de focus visibles (styles focus + skip link visible au focus)
- `[x] T-ACC014` Trap focus pour modales (dans `src/web/static/ts/components/modal.ts`)
- `[x] T-ACC015` Restauration du focus après fermeture modale
- `[x] T-ACC016` Roving tabindex implémenté pour les listes filtres catégories/tags (desktop + mobile)
- `[x] T-ACC017` Documenter les raccourcis clavier (`docs/KEYBOARD_SHORTCUTS.md`)
- `[x] T-ACC018` Raccourci `?` pour aide clavier (modal d'aide des raccourcis, dispo sur toutes les pages)
- `[x] T-ACC008` Landmarks ARIA (`header`/`main`) + skip link sur templates actifs
- `[x] T-ACC009` Hiérarchie des titres validée sur templates actifs (1 `h1`/page, sans saut de niveau)
- `[x] T-ACC010` Régions live ARIA identifiées et documentées (`docs/ACCESSIBILITY_LANDMARKS_LIVE_REGIONS.md`)
- `[x] T-ACC012` Navigation par landmarks implémentée avec aide dédiée (modal `?` + landmarks dynamiques)
- `[x] T-ACC020` Associations `label`/`for`: audit global terminé + corrections appliquées sur tous les templates (labels explicites pour checkboxes/file inputs, ids cohérents)
- `[x] T-ACC046` Tests axe-core Playwright (règles WCAG 2.0/2.1 A/AA)
- `[x] T-ACC047` Ajouter étape CI accessibilité (Forgejo Actions: axe + Lighthouse)
- `[x] T-ACC042` Respecter `prefers-reduced-motion` (désactivation animations/transitions)
- `[x] T-ACC028` Indicateur favori hors couleur seule (icône + `aria-pressed` + label add/remove)
- `[x] T-ACC030` Liens non uniquement par couleur (soulignage dans `main`)
- `[x] T-ACC005` Audit automatique exécuté sur routes publiques et protégées (validation dev `http://127.0.0.1:8003`)
- `[x] T-ACC019` Navigation première lettre (typeahead + support IME/composition): prompts, filtres catégories/tags, historique versions, tableaux manage/admin (annonce SR localisée)
- `[x] T-ACC022` `aria-describedby` global: tous les textes d'aide/erreur inline sont reliés aux champs (auth, import/export, backup, manage, admin, modales)
- `[x] T-ACC023` Résumé d'erreurs en haut des formulaires: bannières sur tous les formulaires principaux (auth/import-export/backup/manage/admin + éditeur de prompt), liens vers champs en erreur + focus sur le premier champ invalide

### Tâches partiellement implémentées

- `[~] T-ACC024` Liaison erreurs/champs (`aria-invalid` + `aria-describedby` + focus) sur auth + import/export + backup + manage categories/tags + admin users (create), extension restante globale
- `[~] T-ACC025` Annonces de validation améliorées (live regions + résumés d'erreurs + navigation clavier) étendues aux formulaires principaux + remplacement des `alert` bloquants sur manage categories/tags, couverture temps réel complète restante
- `[~] T-ACC024..025` Formulaire d'édition/creation de prompt: `aria-invalid` + couverture temps réel (reste: validation temps réel complète et autres formulaires secondaires)
- `[~] T-ACC021` `aria-label`/noms accessibles: ajout d'un nom accessible pour la checkbox de sélection de prompt (liaison `aria-labelledby` au titre) + localisation des libellés (aide `?`, favoris), audit global restant
- `[~] T-ACC033` Icônes décoratives: ajout `aria-hidden="true"`/`focusable="false"` sur SVG décoratifs (recherche, menus, sidebar), audit global restant
- `[~] T-ACC029` Différencier états success/error/warning: notifications renforcées (role/aria-live cohérents), extension restante aux autres patterns visuels

### Tâches restantes

- `[ ]` Toutes les autres tâches du plan, notamment:
- `[ ] T-ACC006` / `[ ] T-ACC007` Audit clavier manuel + lecteurs d'écran
- `[ ] T-ACC024` à `[ ] T-ACC025` couverture formulaires/erreurs temps réel complète
- `[ ] T-ACC026` à `[ ] T-ACC030` audit contraste complet + indicateurs hors couleur
- `[ ] T-ACC031` à `[ ] T-ACC034` images/icônes (alt/aria-hidden) complet
- `[ ] T-ACC035` à `[ ] T-ACC039` composants avancés (modales/tabs/tooltips) conformité complète
- `[ ] T-ACC040` à `[ ] T-ACC045` préférences accessibilité (contraste élevé, reduced motion, taille texte)
- `[ ] T-ACC048` à `[ ] T-ACC050` CI + validation manuelle + audit final
- `[ ] T-ACC051` à `[ ] T-ACC053` documentation finale + déclaration accessibilité

---

## Phase 1: Fondation et Outils (3-4 jours)

### 1.1 Installation des outils de test d'accessibilité

**Objectif:** Établir l'infrastructure de test pour identifier et valider les problèmes d'accessibilité.

#### Tâches

**[T-ACC001]** Configurer axe-core pour les tests navigateur

- Emplacement: `playwright.config.ts`
- Détails: Ajouter l'intégration axe-core pour les tests Playwright
- Dépendances: `@axe-core/playwright`

**[T-ACC002]** Configurer les tests Lighthouse CI

- Emplacement: `.github/workflows/` (ou `.forgejo/workflows/`)
- Détails: Ajouter une étape de test accessibilité dans le pipeline CI
- Métriques cibles: Score accessibilité ≥ 95

**[T-ACC003]** Créer un script de test d'accessibilité local

- Emplacement: `scripts/accessibility_test.py`
- Détails: Script Python pour audits automatisés avec axe-core
- Commandes: `python scripts/accessibility_test.py --verbose`

**[T-ACC004]** Documenter les outils d'accessibilité pour les développeurs

- Emplacement: `docs/ACCESSIBILITY_TESTING.md`
- Détails: Guide d'utilisation de axe-core, Lighthouse, WAVE

### 1.2 Audit initial complet

**Objectif:** Identifier tous les problèmes d'accessibilité actuels avec des outils automatisés et manuels.

#### Tâches

**[T-ACC005]** Effectuer un audit automatique avec axe-core

- Pages à tester: `/`, `/import-export`, `/backup-management`, `/profile`, `/admin/users`
- Outils: axe DevTools, Lighthouse
- Livrable: Rapport listant toutes les violations

**[T-ACC006]** Tester la navigation au clavier seule

- Vérifier: Tab, Shift+Tab, Entrée, Échap, Flèches
- Documenter: Tous les éléments focusables, l'ordre logique, les pièges au clavier

**[T-ACC007]** Tester avec lecteurs d'écran (NVDA, VoiceOver)

- Équipes: Au moins 2 testeurs avec lecteurs d'écran
- Livrable: Notes sur l'expérience utilisateur avec lecteurs d'écran

---

## Phase 2: Structure Sémantique et Landmarks (3-4 jours)

### 2.1 Structure HTML sémantique

**Objectif:** Corriger la structure HTML pour une meilleure sémantique et navigation par lecteurs d'écran.

#### Fichiers cibles: `src/web/templates/*.html`

#### Tâches

**[T-ACC008]** Ajouter ou corriger les landmarks ARIA

```
- <header> avec role="banner"
- <main> avec role="main" 
- <nav> avec role="navigation"
- <footer> avec role="contentinfo"
- <aside> avec role="complementary"
```

**[T-ACC009]** Corriger la hiérarchie des titres (h1-h6)

- Vérifier: Un seul h1 par page, hiérarchie logique sans saut de niveau
- Pages à vérifier: Toutes les pages du site

**[T-ACC010]** Identifier et documenter les régions live ARIA

- Emplacement: Zones de notification, mise à jour dynamique du contenu
- Attribut: `aria-live="polite"` pour les notifications non urgentes
- Attribut: `aria-live="assertive"` pour les erreurs critiques

### 2.2 Navigation et Skip Links

**Objectif:** Permettre aux utilisateurs de clavier de sauter le contenu répétitif.

#### Tâches

**[T-ACC011]** Créer le lien "Aller au contenu principal"

- Emplacement: Première position dans `<body>`
- Style: Visible au focus, caché visuellement sinon
- Raccourci: Touche Tab révèle le lien

```html
<a href="#main-content" class="skip-link">
  Aller au contenu principal
</a>
```

**[T-ACC012]** Implémenter la navigation par landmarks

- Raccourci clavier: [?] pour afficher la liste des régions
- Documentation: Section dans l'aide/modal

---

## Phase 3: Focus et Navigation Clavier (4-5 jours)

### 3.1 Gestion du focus

**Objectif:** Assurer une navigation au clavier fluide et intuitive.

#### Tâches

**[T-ACC013]** Ajouter des indicateurs de focus visibles

- Emplacement: `src/web/static/css/tailwind-globals.css`
- Style: Outline visible (2px solid, contraste 3:1 minimum)
- Couleur: `--color-focus` avec `focus-visible:ring`

```css
:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
```

**[T-ACC014]** Implémenter le trap focus pour les modales

- Comportement: Tab/Shift+Tab reste dans la modale
- Ouverture: Focus sur premier élément focusable
- Fermeture: Retour focus sur élément déclencheur
- Fichier: `src/web/static/ts/components/modal.ts`

**[T-ACC015]** Implémenter la restauration du focus

- Après fermeture modale: Retour au bouton/lien déclencheur
- Après suppression: Focus sur élément contextuel

**[T-ACC016]** Implémenter roving tabindex pour les listes

- Composants: Onglets, listes de sélection, groupes de boutons
- Comportement: Un seul élément tabbable à la fois
- Navigation: Flèches pour naviguer entre éléments

```typescript
// Exemple roving tabindex
items.forEach((item, index) => {
  item.setAttribute('tabindex', index === 0 ? '0' : '-1');
  item.setAttribute('role', 'tab');
});
```

### 3.2 Raccourcis clavier

**Objectif:** Documenter et implémenter les raccourcis clavier pour navigation efficace.

#### Tâches

**[T-ACC017]** Documenter les raccourcis existants

- Emplacement: `docs/KEYBOARD_SHORTCUTS.md`
- Raccourcis actuels: Cmd+H/Ctrl+H (historique version)

**[T-ACC018]** Ajouter raccourci [?] pour aide

- Emplacement: `src/web/static/ts/app.ts`
- Action: Ouvre modal d'aide avec liste des raccourcis
- Événement: `keydown` sur fenêtre

**[T-ACC019]** Ajouter navigation par：第一字母快速跳转（中文输入场景）

- Emplacement: Listes de prompts, catégories, tags
- Comportement: Lettres pour naviguer rapidement
- Feedback: Annonce screen reader "导航到 { lettre }"

---

## Phase 4: Formulaires et Champs (3-4 jours)

### 4.1 Labels et associations

**Objectif:** Assurer que tous les champs de formulaire ont des labels visibles et associés.

#### Fichiers cibles: `src/web/templates/*.html`, `src/web/static/ts/components/form.ts`

#### Tâches

**[T-ACC020]** Associer tous les labels à leurs inputs

- Attribut: `for="id"` sur label, `id="id"` sur input
- Exemple:

```html
<label for="prompt-title">Titre du prompt</label>
<input id="prompt-title" name="title" type="text">
```

**[T-ACC021]** Ajouter aria-label aux inputs sans label visible

- Champs: Recherche, filtres rapides
- Exemple:

```html
<input type="text" aria-label="Rechercher prompts">
```

**[T-ACC022]** Implémenter aria-describedby pour aide contextuelle

```html
<input id="password" type="password" aria-describedby="password-hint">
<span id="password-hint">Min. 12 caractères</span>
```

### 4.2 Messages d'erreur et validation

**Objectif:** Rendre les erreurs de formulaire accessibles.

#### Tâches

**[T-ACC023]** Créer zone de résumé des erreurs en haut du formulaire

- Attribut: `aria-live="polite"`
- Contient: Liens vers chaque champ en erreur
- Focus: Premier champ en erreur après affichage

**[T-ACC024]** Associer messages d'erreur aux champs

```html
<input id="email" aria-invalid="true" aria-describedby="email-error">
<span id="email-error" role="alert">Email invalide</span>
```

**[T-ACC025]** Annoncer état de validation en temps réel

```typescript
input.addEventListener('input', () => {
  if (input.validity.valid) {
    announceToScreenReader('Champ valide');
  }
});
```

---

## Phase 5: Couleurs et Contraste (2-3 jours)

### 5.1 Audit des couleurs

**Objectif:** Identifier et corriger tous les problèmes de contraste couleur.

#### Tâches

**[T-ACC026]** Auditer tous les textes contre le fond

- Outil: WebAIM Contrast Checker
- Seuil WCAG AA: 4.5:1 (normal), 3:1 (grand text 18px+)

**[T-ACC027]** Auditer les composants UI

- Boutons, badges, icônes, bordures
- Vérifier: Texte sur boutons, icônes informatives

### 5.2 Indicateurs au-delà de la couleur

**Objectif:** Ne pas utiliser la couleur comme seul moyen de transmettre de l'information.

#### Tâches

**[T-ACC028]** Ajouter icônes aux favoris (actuellement couleur seule)

- Emplacement: Cartes de prompts
- Avant: Fond jaune seul
- Après: Icône + couleur + icône étole

```html
<button class="favorite-btn" aria-label="Retirer des favoris">
  <svg aria-hidden="true" class="text-yellow-500">
    <use href="#icon-star-filled"></use>
  </svg>
  <span class="sr-only">Favori</span>
</button>
```

**[T-ACC029]** Différencier états success/error/warning

- Avant: Rouge/vert/orange seuls
- Après: Icône + couleur + texte explicite

**[T-ACC030]** Marquer les liens sans couleur seule

- Soulignage ou différence de poids

```css
a:not(.btn):not(.icon-link) {
  text-decoration: underline;
}
```

---

## Phase 6: Images et Médias (1-2 jours)

### 6.1 Texte alternatif

**Objectif:** Toutes les images et icônes informatives ont un texte alternatif.

#### Fichiers cibles: `src/web/templates/*.html`, composants TypeScript

#### Tâches

**[T-ACC031]** Ajouter alt aux images de contenu

```html
<img src="docs/images/gallery/promptvault_loginpage.jpg" 
     alt="Page de connexion PromptVault avec champs username et mot de passe">
```

**[T-ACC032]** Ajouter aria-label aux icônes interactives

```html
<button aria-label="Supprimer le prompt" class="icon-btn">
  <svg aria-hidden="true"><use href="#icon-trash"></use></svg>
</button>
```

**[T-ACC033]** Masquer icônes décoratives

```html
<svg aria-hidden="true" class="decorative-icon">
  <use href="#icon-decoration"></use>
</svg>
```

**[T-ACC034]** Ajouter aria-hidden aux logos décoratifs

```html
<a href="/">
  <img src="logo.svg" alt="" aria-hidden="true">
</a>
```

---

## Phase 7: Composants Interactifs Avancés (3-4 jours)

### 7.1 Modales

**Objectif:** Modales complètement accessibles avec gestion focus et ARIA.

#### Fichier: `src/web/static/ts/components/modal.ts`

#### Tâches

**[T-ACC035]** Ajouter role et attributs ARIA

```html
<div role="dialog" 
     aria-modal="true" 
     aria-labelledby="modal-title"
     aria-describedby="modal-desc">
  <h2 id="modal-title">Titre de la modale</h2>
  <div id="modal-desc">Description</div>
  <!-- Contenu -->
</div>
```

**[T-ACC036]** Implémenter focus trap complet

- Bloquer Tab/Shift+Tab hors de la modale
- Gestion Échap pour fermer
- Gestion Tab circulaire dans la modale

**[T-ACC037]** Gérer focus à l'ouverture/fermeture

```typescript
function openModal(trigger: HTMLElement) {
  const focusable = modal.querySelectorAll(FOCUSABLE_SELECTOR);
  firstFocusable = focusable[0];
  lastFocusable = focusable[focusable.length - 1];
  
  firstFocusable.focus();
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  trigger.focus();
  document.body.style.overflow = '';
}
```

### 7.2 Listes et onglets (Tabs)

**Objectif:** Implémenter le pattern ARIA tablist correctement.

#### Tâches

**[T-ACC038]** Implémenter pattern ARIA tabs

```html
<div role="tablist" aria-label="Catégories">
  <button role="tab" 
          aria-selected="true" 
          aria-controls="panel-1" 
          id="tab-1"
          tabindex="0">
    Tous
  </button>
  <button role="tab" 
          aria-selected="false" 
          aria-controls="panel-2" 
          id="tab-2"
          tabindex="-1">
    Favoris
  </button>
</div>

<div role="tabpanel" 
     id="panel-1" 
     aria-labelledby="tab-1">
  <!-- Contenu -->
</div>
```

### 7.3 Tooltips

**Objectif:** Tooltips accessibles via ARIA describedby.

#### Tâches

**[T-ACC039]** Implémenter tooltips accessibles

```html
<button aria-describedby="tooltip-save">
  Sauvegarder
  <span id="tooltip-save" role="tooltip" class="tooltip">
    Enregistre les modifications
  </span>
</button>
```

---

## Phase 8: Paramètres d'Accessibilité (2-3 jours)

### 8.1 Mode contraste élevé

**Objectif:** Offrir un mode pour utilisateurs nécessitant plus de contraste.

#### Tâches

**[T-ACC040]** Créer toggle dans paramètres utilisateur

- Emplacement: Page profil / paramètres
- Stockage: `localStorage` + préférence utilisateur BDD
- Action: Ajoute classe `high-contrast` au body

**[T-ACC041]** Définir styles contraste élevé

```css
.high-contrast {
  --color-primary: #0000ff;
  --color-text: #000000;
  --color-bg: #ffffff;
  --border-width: 3px;
}

.high-contrast a {
  text-decoration: underline;
  font-weight: bold;
}
```

### 8.2 Réduction des animations

**Objectif:** Respecter la préférence système `prefers-reduced-motion`.

#### Tâches

**[T-ACC042]** Ajuster animations CSS

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation: none !important;
    transition: none !important;
  }
}
```

**[T-ACC043]** Ajouter préférence dans paramètres

- Option: "Réduire les animations"
- Stockage: Préférence utilisateur

### 8.3 Ajustement taille texte

**Objectif:** Permettre agrandissement du texte jusqu'à 200%.

#### Tâches

**[T-ACC044]** Implémenter contrôles taille police

- Emplacement: Pied de page ou paramètres
- Options: 100%, 125%, 150%, 175%, 200%
- Application: `font-size` sur html ou body

**[T-ACC045]** Vérifier layout responsive

- Pas de scroll horizontal à 200%
- Pas de texte tronqué
- Composants fluides

---

## Phase 9: Tests et Validation (3-4 jours)

### 9.1 Tests automatisés

**Objectif:** Intégrer tests d'accessibilité dans CI/CD.

#### Tâches

**[T-ACC046]** Créer tests axe-core Playwright

```typescript
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('homepage has no accessibility violations', async ({ page }) => {
  const accessibilityScanResults = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  
  expect(accessibilityScanResults.violations).toEqual([]);
});
```

**[T-ACC047]** Ajouter étape CI accessibilité

- Emplacement: Pipeline CI/CD
- Action: Fail si violations critiques

### 9.2 Tests manuels

**Objectif:** Valider manuellement l'expérience utilisateurs.

#### Tâches

**[T-ACC048]** Créer checklist tests clavier

- Document: `docs/ACCESSIBILITY_CHECKLIST.md`
- Couvre: Toutes les fonctionnalités principales

**[T-ACC049]** Tests avec lecteurs d'écran

- NVDA (Windows)
- VoiceOver (macOS)
- Documentation: Notes par fonctionnalité

### 9.3 Audit final

**Objectif:** Confirmer conformité WCAG 2.1 AA.

#### Tâches

**[T-ACC050]** Audit externe (optionnel)

- Outil: WAVE, axe, Lighthouse
- Score cible: 100%

---

## Phase 10: Documentation (1-2 jours)

### 10.1 Documentation développeur

**Objectif:** Guide pour maintenir l'accessibilité.

#### Tâches

**[T-ACC051]** Créer guide accessibilité développeurs

- Emplacement: `docs/ACCESSIBILITY_GUIDELINES.md`
- Contenu:
  - Principes WCAG 2.1 AA
  - Patterns ARIA courants
  - Checklist avant merge
  - Outils de test

**[T-ACC052]** Documenter composants accessibles

- Emplacement: `docs/COMPONENTS_ACCESSIBILITY.md`
- Chaque composant: Exemple ARIA correct

### 10.2 Déclaration d'accessibilité

**Objectif:** Documenter le niveau de conformité.

#### Tâches

**[T-ACC053]** Créer page déclaration accessibilité

- Emplacement: `/accessibility-statement`
- Contenu:
  - Niveau de conformité (AA)
  - Méthodes de test
  - Limites connues
  - Contact accessibilité

---

## Matrice des Dépendances

```
Phase 1: Fondation
    ↓
Phase 2: Structure Sémantique (dépend de Phase 1)
    ↓
Phase 3: Focus/Clavier (dépend de Phase 2)
    ↓
Phase 4: Formulaires (dépend de Phase 2)
    ↓
Phase 5: Couleurs (dépend de Phase 1)
    ↓
Phase 6: Images (dépend de Phase 2)
    ↓
Phase 7: Composants (dépend de Phase 3)
    ↓
Phase 8: Paramètres (dépend de Phase 5)
    ↓
Phase 9: Tests (dépend de toutes les phases)
    ↓
Phase 10: Documentation (dépend de Phase 9)
```

## Fichiers à Modifier

### Templates HTML

- `src/web/templates/index.html`
- `src/web/templates/import_export.html`
- `src/web/templates/backup_management.html`

### Styles CSS

- `src/web/static/css/tailwind-globals.css`
- `src/web/static/css/style.css` (si existe encore)

### Composants TypeScript

- `src/web/static/ts/app.ts`
- `src/web/static/ts/components/modal.ts`
- `src/web/static/ts/components/form.ts`
- `src/web/static/ts/components/tabs.ts`

### Configuration

- `playwright.config.ts`
- `.github/workflows/` (ou `.forgejo/workflows/`)

### Documentation

- `docs/ACCESSIBILITY_GUIDELINES.md` (nouveau)
- `docs/ACCESSIBILITY_TESTING.md` (nouveau)
- `docs/COMPONENTS_ACCESSIBILITY.md` (nouveau)

## Estimations par Tâche

| Phase | Tâches | Jours estimés |
|-------|--------|---------------|
| Phase 1 | 4 | 3-4 |
| Phase 2 | 3 | 3-4 |
| Phase 3 | 4 | 4-5 |
| Phase 4 | 4 | 3-4 |
| Phase 5 | 3 | 2-3 |
| Phase 6 | 4 | 1-2 |
| Phase 7 | 4 | 3-4 |
| Phase 8 | 4 | 2-3 |
| Phase 9 | 4 | 3-4 |
| Phase 10 | 2 | 1-2 |
| **Total** | **36** | **~21 jours** |

## Critères de Succès

1. Score Lighthouse Accessibilité ≥ 95
2. 0 violations axe-core critiques
3. Navigation clavier complète (Tab, Entrée, Échap, Flèches)
4. Lecture d'écran fonctionnelle (NVDA, VoiceOver)
5. Contraste couleurs conforme (4.5:1 minimum)
6. Documentation complète pour développeurs
7. Déclaration d'accessibilité publiée

## Notes

- Ce plan est compatible avec i18n existant (4 langues)
- Tous les texts visibles添加 doivent être dans les fichiers de traduction
- Tests unitaires requis pour nouveaux composants accessibles
- Review d'accessibilité requise avant chaque merge
