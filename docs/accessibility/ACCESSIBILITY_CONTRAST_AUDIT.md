# Audit de Contraste WCAG 2.1 AA - PromptVault

**Dernière mise à jour:** 2026-02-18
**Statut:** Guide complet pour audits manuels T-ACC026 et T-ACC027

## Vue d'ensemble

Ce document fournit des checklists détaillées pour tester manuellement:
- **T-ACC026:** Contraste texte/fond WCAG 2.1 AA (4.5:1 normal, 3:1 grand texte)
- **T-ACC027:** Contraste composants UI (boutons, icônes, bordures, etc.)

---

## Rappel des Normes WCAG 2.1 AA

### Niveaux de Contraste Requis

| Type de texte | Rapport minimal | Condition |
|---|---|---|
| Texte normal | 4.5:1 | < 18px ou < 14px bold |
| Grand texte | 3:1 | ≥ 18px ou ≥ 14px bold |
| Composants UI | 3:1 | Bordure, outline, focus indicator |
| Icônes | 3:1 | Si informative/non-décorative |
| Arrière-plan | 3:1 | Boutons, badge, etc. |

### Outils Recommandés

- **Lighthouse (intégré):** DevTools → Lighthouse → Accessibility
- **WAVE Web Accessibility Evaluation Tool:** wave.webaim.org
- **WebAIM Contrast Checker:** webaim.org/resources/contrastchecker
- **Deque Axe DevTools:** Extension navigateur
- **Color Contrast Analyzer:** Outil desktop (Thomson Reuters)

---

## Section 1: Audit Texte/Fond (T-ACC026)

### 1.1 Préparation

- [ ] Ouvrir page sur http://127.0.0.1:8003
- [ ] Ouvrir DevTools (F12)
- [ ] Utiliser outil "Inspect" pour vérifier couleurs
- [ ] Noter tous les contraires insuffisants dans checklist

### 1.2 Texte Normal (Exige 4.5:1)

#### Page d'accueil (`/`)

**Header Navigation**
- [ ] Logo text (si présent): `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Nav links (Accueil, Catégories, Tags): `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Nav links hover: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Search bar**
- [ ] Input placeholder text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Input entered text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Prompt Cards**
- [ ] Prompt title: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Prompt description: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Category tag: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Category tag hover: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Footer**
- [ ] Footer text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Footer links: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

#### Pages d'Authentification (`/auth/login`, `/auth/register`, `/auth/forgot-password`)

**Form Labels**
- [ ] Label text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Form Inputs**
- [ ] Input text (normal): `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Input placeholder: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Input focus outline: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1, voir Section 2)
  - Notes: ___________

**Form Buttons**
- [ ] Button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Button hover text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Error Messages**
- [ ] Error text (if any): `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Error background (if colored): Voir Section 2
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

**Links (Login / Register / Forgot Password)**
- [ ] Link text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Link hover: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

#### Pages de Gestion (`/backup-management`, `/import-export`, etc.)

**Page Title (H1)**
- [ ] Title text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Section Headings (H2, H3)**
- [ ] H2 text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] H3 text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Form Labels & Inputs**
- [ ] Input label: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Input text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Input placeholder: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Select dropdown text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Help Text & Instructions**
- [ ] Help text (aria-describedby): `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Error message text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Buttons**
- [ ] Primary button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Secondary button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Danger/Delete button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Tables (si présentes)**
- [ ] Table header text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Table cell text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Table row hover text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Notifications/Alerts**
- [ ] Success message text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Warning message text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Error message text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

#### Pages Admin (`/admin/users`, `/admin/sessions`)

**Admin Navigation**
- [ ] Admin menu text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Active menu item text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Tables**
- [ ] Table header: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Table cell: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Status badge (active/inactive): `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Buttons**
- [ ] Edit button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Delete button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

#### Page Profil (`/profile`)

**Profile Form**
- [ ] Label text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Input text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

**Change Password**
- [ ] Instruction text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] Validation message: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

---

## Section 2: Audit Composants UI (T-ACC027)

### 2.1 Boutons et Indicateurs Focus

#### Focus Indicators

**Requirement:** Outline ou ring visible avec ratio 3:1

- [ ] **Boutons focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Visible: ✓
  - Offset: ✓ (> 2px)
  - Notes: ___________

- [ ] **Input focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Visible: ✓
  - Offset: ✓ (> 2px)
  - Notes: ___________

- [ ] **Link focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Visible: ✓
  - Notes: ___________

- [ ] **Checkbox focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Visible: ✓
  - Notes: ___________

**Pages à tester:**
- [ ] Page d'accueil
- [ ] Page d'authentification
- [ ] Backup Management
- [ ] Import/Export
- [ ] Manage Categories
- [ ] Manage Tags
- [ ] Admin Users
- [ ] Admin Sessions

#### Boutons Primaires

- [ ] **Button primary text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Button primary background:** Pas d'exigence seule couleur
  - Mais: Texte sur fond ✓ (voir ci-dessus)

- [ ] **Button primary border/outline au focus:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Button primary hover:** Texte contraste maintenu
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Button primary disabled:** Text grisé
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

#### Boutons Secondaires

- [ ] **Button secondary text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Button secondary border:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Button secondary focus:** Outline visible
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

#### Boutons Danger

- [ ] **Delete button text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Delete button background:** Non-obligatoire seul, mais
  - Texte sur fond: Ratio > 4.5:1
  - Notes: ___________

- [ ] **Delete button border au focus:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

### 2.2 Entrées de Formulaire

#### Input Borders

- [ ] **Input border (normal):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Input border (focus):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Input border (error):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Input border (disabled):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

#### Input Placeholders

- [ ] **Placeholder text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

#### Input Labels

- [ ] **Label for text input:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Label for password input:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Label for checkbox:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Label for select:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

### 2.3 Checkboxes et Radios

#### Checkbox States

- [ ] **Checkbox border (unchecked):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Checkbox checkmark (checked):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Checkbox focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Visible: ✓
  - Notes: ___________

- [ ] **Checkbox disabled:** Texte + border grisé
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

#### Radio Button States

- [ ] **Radio border (unchecked):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Radio dot (checked):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Radio focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

### 2.4 Icônes Informatives

#### Icon Colors

- [ ] **Edit icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1 si informative)
  - Notes: ___________

- [ ] **Delete/Trash icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Star/Favorite icon (unfilled):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Star/Favorite icon (filled):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Warning/Alert icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Success icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Error icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

### 2.5 Badges et Tags

#### Category Tags

- [ ] **Category badge text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Category badge background:** Texte on fond ratio ✓ (see above)
  - Notes: ___________

- [ ] **Category badge border (if any):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Category badge hover:** Contraste maintenu
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

#### Status Badges

- [ ] **Active status badge:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Inactive status badge:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Warning status badge:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

### 2.6 Messages et Alertes

#### Error Messages

- [ ] **Error text color:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Error icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Error background (if colored):** Texte on fond ratio ✓
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Error border:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

#### Success Messages

- [ ] **Success text color:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Success icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Success background (if colored):** Texte on fond ratio ✓
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

#### Warning Messages

- [ ] **Warning text color:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Warning icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

### 2.7 Tables

#### Table Headers

- [ ] **Header text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Header background:** Texte on fond ratio ✓
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Header border:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

#### Table Cells

- [ ] **Cell text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Cell border:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Row hover (background):** Texte on hover bg ratio ✓
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

#### Table Sorting

- [ ] **Sort indicator (arrow):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Sortable header text (visual indicator):** Texte + sort indicator
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

### 2.8 Liens

#### Normal Links

- [ ] **Link text (in paragraph):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Link underline (if present):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Link hover text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Link focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

#### Link States

- [ ] **Unvisited link:** Contraste ✓
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Visited link (if different):** Contraste ✓
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Link disabled:** Grisé, contraste ✓
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

### 2.9 Modales et Dialogs

#### Modal Overlay

- [ ] **Modal overlay (backdrop):** Contraste texte/backdrop OK
  - Notes: ___________

#### Modal Content

- [ ] **Modal title:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Modal button text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Modal close button (X icon):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Modal focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

### 2.10 Dropdowns et Selects

#### Dropdown/Select States

- [ ] **Select label:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Select border (closed):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 3:1)
  - Notes: ___________

- [ ] **Select text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Dropdown option text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Dropdown option hover:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

- [ ] **Dropdown option selected:** Texte + background ratio ✓
  - Ratio: ____ ✓ (> 4.5:1)
  - Notes: ___________

---

## Section 3: Checklist de Problèmes de Contraste

Pour chaque problème trouvé, noter:

- [ ] **URL/Page:** _______________
- [ ] **Élément affecté:** (ex: "Bouton sauvegarder", "Texte label")
- [ ] **Couleurs actuelles:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
- [ ] **Ratio actuel:** ____ (cible: ≥ 4.5:1 ou ≥ 3:1)
- [ ] **Type:**
  - [ ] Texte normal (exige 4.5:1)
  - [ ] Texte grand (exige 3:1)
  - [ ] Composant UI (exige 3:1)
  - [ ] Focus indicator (exige 3:1)
- [ ] **Sévérité:**
  - [ ] Critique (texte normal < 4.5:1)
  - [ ] Haute (composant UI < 3:1)
  - [ ] Moyenne (borderline)
  - [ ] Basse (amélioration)
- [ ] **Suggestion de correctif:**
  - [ ] Éclaircir texte (current: _____, target: _____)
  - [ ] Assombrir texte (current: _____, target: _____)
  - [ ] Modifier fond (current: _____, target: _____)
  - [ ] Ajouter border/outline
  - [ ] Augmenter épaisseur
- [ ] **Outil utilisé:** WAVE / WebAIM / Axe / DevTools Lighthouse
- [ ] **Notes:** _______________

---

## Ressources et Outils

### Calculateurs de Contraste

1. **WebAIM Contrast Checker**
   - URL: https://webaim.org/resources/contrastchecker
   - Entrée: Couleur #hex
   - Sortie: Ratio WCAG AA/AAA

2. **Contrast Ratio**
   - URL: https://www.contrastchecker.com/
   - Interface simple
   - Calcul en temps réel

3. **Color Contrast Analyzer (Outil)**
   - Windows/Mac/Linux
   - Prélèvement de couleur sur écran
   - Calcul ratio automatique

### Extensions Navigateur

- **WAVE WebAIM:** Audit complet page
- **Axe DevTools:** Violations WCAG automatiques
- **Lighthouse (Chrome):** Score accessibilité intégré
- **Color Contrast Analyzer:** Vérification rapide couleurs

### Documentation

- WCAG 2.1 Contraste: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html
- Non-Text Contraste: https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html
- Color Blindness Simulator: https://www.color-blindness.com/coblis-color-blindness-simulator/

---

## Matrice de Test Résumée

| Page | Texte (4.5:1) | Composants (3:1) | Buttons | Links | Status |
|------|---|---|---|---|---|
| `/` | [ ] | [ ] | [ ] | [ ] | |
| `/auth/login` | [ ] | [ ] | [ ] | [ ] | |
| `/auth/register` | [ ] | [ ] | [ ] | [ ] | |
| `/backup-management` | [ ] | [ ] | [ ] | [ ] | |
| `/import-export` | [ ] | [ ] | [ ] | [ ] | |
| `/manage-categories` | [ ] | [ ] | [ ] | [ ] | |
| `/manage-tags` | [ ] | [ ] | [ ] | [ ] | |
| `/admin/users` | [ ] | [ ] | [ ] | [ ] | |
| `/admin/sessions` | [ ] | [ ] | [ ] | [ ] | |
| `/profile` | [ ] | [ ] | [ ] | [ ] | |

---

## Notes Importantes

1. **Environnement:** Tester sur `http://127.0.0.1:8003`
2. **Résolution:** Tester sur 1920x1080 (desktop)
3. **Navigateur:** Firefox + Chrome (les deux)
4. **Light/Dark modes:** Tester les deux si applicable
5. **Zoom:** Tester à 100%, 125%, 150%
6. **Enregistrement:** Créer issues GitHub avec tag `a11y` et `contrast`
7. **Temps estimé:** 2-3 heures pour audit complet

---

## Template d'Issue GitHub

```markdown
## Problème de Contraste WCAG 2.1 AA

**Page:** [URL]
**Élément:** [Description]

### Couleurs Actuelles
- Texte: rgb(?, ?, ?)
- Fond: rgb(?, ?, ?)
- Ratio: [X]:1 (cible: 4.5:1 ou 3:1)

### Type
- [ ] Texte normal
- [ ] Texte grand
- [ ] Composant UI
- [ ] Focus indicator

### Suggestion de Correctif
[Proposer nouvelle couleur et nouveau ratio]

### Outil utilisé
[WAVE / WebAIM / Axe / DevTools]

**Sévérité:** Critique / Haute / Moyenne / Basse
```
