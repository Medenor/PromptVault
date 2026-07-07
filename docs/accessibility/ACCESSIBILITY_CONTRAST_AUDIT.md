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

| Type de texte | Rapport minimal | Condition                         |
| ------------- | --------------- | --------------------------------- |
| Texte normal  | 4.5:1           | < 18px ou < 14px bold             |
| Grand texte   | 3:1             | ≥ 18px ou ≥ 14px bold             |
| Composants UI | 3:1             | Bordure, outline, focus indicator |
| Icônes        | 3:1             | Si informative/non-décorative     |
| Arrière-plan  | 3:1             | Boutons, badge, etc.              |

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
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Nav links (Accueil, Catégories, Tags): `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Nav links hover: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Search bar**

- [ ] Input placeholder text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Input entered text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Prompt Cards**

- [ ] Prompt title: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Prompt description: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Category tag: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Category tag hover: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Footer**

- [ ] Footer text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Footer links: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

#### Pages d'Authentification (`/auth/login`, `/auth/register`, `/auth/forgot-password`)

**Form Labels**

- [ ] Label text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Form Inputs**

- [ ] Input text (normal): `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Input placeholder: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Input focus outline: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1, voir Section 2)
  - Notes: ****\_\_\_****

**Form Buttons**

- [ ] Button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Button hover text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Error Messages**

- [ ] Error text (if any): `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Error background (if colored): Voir Section 2
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

**Links (Login / Register / Forgot Password)**

- [ ] Link text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Link hover: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

#### Pages de Gestion (`/backup-management`, `/import-export`, etc.)

**Page Title (H1)**

- [ ] Title text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Section Headings (H2, H3)**

- [ ] H2 text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] H3 text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Form Labels & Inputs**

- [ ] Input label: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Input text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Input placeholder: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Select dropdown text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Help Text & Instructions**

- [ ] Help text (aria-describedby): `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Error message text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Buttons**

- [ ] Primary button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Secondary button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Danger/Delete button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Tables (si présentes)**

- [ ] Table header text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Table cell text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Table row hover text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Notifications/Alerts**

- [ ] Success message text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Warning message text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Error message text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

#### Pages Admin (`/admin/users`, `/admin/sessions`)

**Admin Navigation**

- [ ] Admin menu text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Active menu item text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Tables**

- [ ] Table header: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Table cell: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Status badge (active/inactive): `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Buttons**

- [ ] Edit button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Delete button text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

#### Page Profil (`/profile`)

**Profile Form**

- [ ] Label text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Input text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

**Change Password**

- [ ] Instruction text: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] Validation message: `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

---

## Section 2: Audit Composants UI (T-ACC027)

### 2.1 Boutons et Indicateurs Focus

#### Focus Indicators

**Requirement:** Outline ou ring visible avec ratio 3:1

- [ ] **Boutons focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Visible: ✓
  - Offset: ✓ (> 2px)
  - Notes: ****\_\_\_****

- [ ] **Input focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Visible: ✓
  - Offset: ✓ (> 2px)
  - Notes: ****\_\_\_****

- [ ] **Link focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Visible: ✓
  - Notes: ****\_\_\_****

- [ ] **Checkbox focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Visible: ✓
  - Notes: ****\_\_\_****

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
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Button primary background:** Pas d'exigence seule couleur
  - Mais: Texte sur fond ✓ (voir ci-dessus)

- [ ] **Button primary border/outline au focus:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Button primary hover:** Texte contraste maintenu
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Button primary disabled:** Text grisé
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

#### Boutons Secondaires

- [ ] **Button secondary text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Button secondary border:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Button secondary focus:** Outline visible
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

#### Boutons Danger

- [ ] **Delete button text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Delete button background:** Non-obligatoire seul, mais
  - Texte sur fond: Ratio > 4.5:1
  - Notes: ****\_\_\_****

- [ ] **Delete button border au focus:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

### 2.2 Entrées de Formulaire

#### Input Borders

- [ ] **Input border (normal):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Input border (focus):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Input border (error):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Input border (disabled):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

#### Input Placeholders

- [ ] **Placeholder text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

#### Input Labels

- [ ] **Label for text input:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Label for password input:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Label for checkbox:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Label for select:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

### 2.3 Checkboxes et Radios

#### Checkbox States

- [ ] **Checkbox border (unchecked):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Checkbox checkmark (checked):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Checkbox focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Visible: ✓
  - Notes: ****\_\_\_****

- [ ] **Checkbox disabled:** Texte + border grisé
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

#### Radio Button States

- [ ] **Radio border (unchecked):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Radio dot (checked):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Radio focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

### 2.4 Icônes Informatives

#### Icon Colors

- [ ] **Edit icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1 si informative)
  - Notes: ****\_\_\_****

- [ ] **Delete/Trash icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Star/Favorite icon (unfilled):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Star/Favorite icon (filled):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Warning/Alert icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Success icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Error icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

### 2.5 Badges et Tags

#### Category Tags

- [ ] **Category badge text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Category badge background:** Texte on fond ratio ✓ (see above)
  - Notes: ****\_\_\_****

- [ ] **Category badge border (if any):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Category badge hover:** Contraste maintenu
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

#### Status Badges

- [ ] **Active status badge:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Inactive status badge:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Warning status badge:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

### 2.6 Messages et Alertes

#### Error Messages

- [ ] **Error text color:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Error icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Error background (if colored):** Texte on fond ratio ✓
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Error border:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

#### Success Messages

- [ ] **Success text color:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Success icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Success background (if colored):** Texte on fond ratio ✓
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

#### Warning Messages

- [ ] **Warning text color:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Warning icon:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

### 2.7 Tables

#### Table Headers

- [ ] **Header text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Header background:** Texte on fond ratio ✓
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Header border:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

#### Table Cells

- [ ] **Cell text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Cell border:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Row hover (background):** Texte on hover bg ratio ✓
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

#### Table Sorting

- [ ] **Sort indicator (arrow):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Sortable header text (visual indicator):** Texte + sort indicator
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

### 2.8 Liens

#### Normal Links

- [ ] **Link text (in paragraph):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Link underline (if present):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Link hover text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Link focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

#### Link States

- [ ] **Unvisited link:** Contraste ✓
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Visited link (if different):** Contraste ✓
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Link disabled:** Grisé, contraste ✓
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

### 2.9 Modales et Dialogs

#### Modal Overlay

- [ ] **Modal overlay (backdrop):** Contraste texte/backdrop OK
  - Notes: ****\_\_\_****

#### Modal Content

- [ ] **Modal title:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Modal button text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Modal close button (X icon):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Modal focus outline:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

### 2.10 Dropdowns et Selects

#### Dropdown/Select States

- [ ] **Select label:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Select border (closed):** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 3:1)
  - Notes: ****\_\_\_****

- [ ] **Select text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Dropdown option text:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Dropdown option hover:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

- [ ] **Dropdown option selected:** Texte + background ratio ✓
  - Ratio: \_\_\_\_ ✓ (> 4.5:1)
  - Notes: ****\_\_\_****

---

## Section 3: Checklist de Problèmes de Contraste

Pour chaque problème trouvé, noter:

- [ ] **URL/Page:** ******\_\_\_******
- [ ] **Élément affecté:** (ex: "Bouton sauvegarder", "Texte label")
- [ ] **Couleurs actuelles:** `rgb(?, ?, ?) on rgb(?, ?, ?)`
- [ ] **Ratio actuel:** \_\_\_\_ (cible: ≥ 4.5:1 ou ≥ 3:1)
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
  - [ ] Éclaircir texte (current: **\_**, target: **\_**)
  - [ ] Assombrir texte (current: **\_**, target: **\_**)
  - [ ] Modifier fond (current: **\_**, target: **\_**)
  - [ ] Ajouter border/outline
  - [ ] Augmenter épaisseur
- [ ] **Outil utilisé:** WAVE / WebAIM / Axe / DevTools Lighthouse
- [ ] **Notes:** ******\_\_\_******

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

| Page                 | Texte (4.5:1) | Composants (3:1) | Buttons | Links | Status |
| -------------------- | ------------- | ---------------- | ------- | ----- | ------ |
| `/`                  | [ ]           | [ ]              | [ ]     | [ ]   |        |
| `/auth/login`        | [ ]           | [ ]              | [ ]     | [ ]   |        |
| `/auth/register`     | [ ]           | [ ]              | [ ]     | [ ]   |        |
| `/backup-management` | [ ]           | [ ]              | [ ]     | [ ]   |        |
| `/import-export`     | [ ]           | [ ]              | [ ]     | [ ]   |        |
| `/manage-categories` | [ ]           | [ ]              | [ ]     | [ ]   |        |
| `/manage-tags`       | [ ]           | [ ]              | [ ]     | [ ]   |        |
| `/admin/users`       | [ ]           | [ ]              | [ ]     | [ ]   |        |
| `/admin/sessions`    | [ ]           | [ ]              | [ ]     | [ ]   |        |
| `/profile`           | [ ]           | [ ]              | [ ]     | [ ]   |        |

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
