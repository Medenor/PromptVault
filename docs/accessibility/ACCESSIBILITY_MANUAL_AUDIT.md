# Manuel d'Audit d'Accessibilité - Tests Clavier et Lecteurs d'Écran

**Dernière mise à jour:** 2026-02-18
**Statut:** Guide complet pour audits manuels T-ACC006 et T-ACC007

## Vue d'ensemble

Ce document fournit des checklists détaillées pour tester manuellement:

- **T-ACC006:** Navigation clavier (Tab, Shift+Tab, Entrée, Échap, Flèches)
- **T-ACC007:** Compatibilité lecteurs d'écran (NVDA, VoiceOver)

---

## Section 1: Audit Clavier (T-ACC006)

### 1.1 Préparation

- [ ] Désactiver la souris ou la cacher
- [ ] Utiliser Firefox ou Chrome en mode standard
- [ ] Ouvrir les DevTools pour inspecter le focus
- [ ] Tester sur desktop (1920x1080 minimum)
- [ ] Enregistrer tous les problèmes avec numéro de ligne/élément

### 1.2 Ordre de Tab - Pages Principales

#### Page d'accueil (`/`)

- [ ] **Skip link visible au premier Tab**
  - [ ] Lien "Aller au contenu principal" visible en haut à gauche
  - [ ] Focus rectangle clair (outline bleu 3px)
  - [ ] Cliquer = saute au `<main id="main-content">`

- [ ] **Navigation clavier du header**
  - [ ] Menu de navigation (accueil, catégories, tags) accessible via Tab
  - [ ] Chaque lien a focus visible
  - [ ] Ordre logique (gauche → droite)

- [ ] **Barre de recherche**
  - [ ] Champ de texte focusable
  - [ ] Placeholder visible sans focus
  - [ ] Label associé (visible ou aria-label)

- [ ] **Grille de prompts**
  - [ ] Chaque carte focusable
  - [ ] Bouton favori accessible (Tab → focus visible)
  - [ ] Lien vers prompt accessible
  - [ ] Ordre: haut → bas, gauche → droite

- [ ] **Footer**
  - [ ] Tous les liens footer focusables
  - [ ] Pas d'éléments cachés dans l'ordre Tab
  - [ ] Focus sur dernier lien = Shift+Tab revient à avant-dernier

#### Page d'authentification (`/auth/login`, `/auth/register`, etc.)

- [ ] **Formulaires d'auth**
  - [ ] Skip link visible en premier
  - [ ] Label → Input → Button ordre logique
  - [ ] Tous les champs focusables
  - [ ] Champs password acceptent Tab (pas d'auto-switch)
  - [ ] Bouton soumission focusable
  - [ ] Lien "Mot de passe oublié" focusable

- [ ] **Messages d'erreur**
  - [ ] Erreurs affichées = focus automatique sur premier champ invalide?
  - [ ] Erreurs annoncées au lecteur d'écran
  - [ ] Lien d'erreur en haut focusable = va au champ

#### Page de gestion (`/backup-management`, `/import-export`, etc.)

- [ ] **Formulaires**
  - [ ] Tous les inputs/selects/checkboxes focusables
  - [ ] Ordre logique (top → bottom)
  - [ ] Boutons soumission focusables
  - [ ] Boutons secondaires (annuler, réinitialiser) focusables

- [ ] **Tableaux/Listes**
  - [ ] Navigable avec Tab seul (roving tabindex)
  - [ ] Lignes éditables focusables
  - [ ] Boutons action (éditer, supprimer) focusables
  - [ ] Flèches (↑↓) pour naviguer dans liste si roving tabindex implémenté

#### Pages Admin (`/admin/users`, `/admin/sessions`)

- [ ] **Menu admin**
  - [ ] Tous les items menu focusables
  - [ ] Ordre logique
  - [ ] Indicateur page active visible

- [ ] **Tableaux utilisateurs/sessions**
  - [ ] Tous les contrôles focusables
  - [ ] Checkbox sélection focusable
  - [ ] Boutons action focusables
  - [ ] Pas de tab trap dans tableau

### 1.3 Indicateurs de Focus - Toutes Pages

- [ ] **Outline visible**
  - [ ] Tous les éléments focusables = outline blue 3px (ou défaut du navigateur)
  - [ ] Outline visible sur fond clair ET fond sombre
  - [ ] Outline offset > 0px (pas collé à l'élément)

- [ ] **Focus pas caché**
  - [ ] Aucun élément avec `visibility: hidden` au focus
  - [ ] Aucun élément avec `opacity: 0` au focus
  - [ ] Scrolling automatique vers élément focusé si hors écran

- [ ] **Focus visible sur hover**
  - [ ] Boutons: focus outline visible même avec hover
  - [ ] Liens: focus outline visible même avec underline
  - [ ] Inputs: focus outline ou ring visible

### 1.4 Touches Spéciales

#### Entrée (Enter) / Espace (Space)

- [ ] **Boutons**
  - [ ] Bouton en focus + Entrée = activation
  - [ ] Bouton en focus + Espace = activation (optionnel mais meilleur)

- [ ] **Checkboxes**
  - [ ] Checkbox en focus + Espace = coché/décoché

- [ ] **Liens**
  - [ ] Lien en focus + Entrée = navigation
  - [ ] Lien en focus + Espace = navigation (optionnel)

- [ ] **Selects/Dropdowns**
  - [ ] Select en focus + Entrée = ouvre dropdown
  - [ ] Select en focus + Flèches = navigation options
  - [ ] Option sélectionnée + Entrée = valide

#### Échap (Escape)

- [ ] **Modales**
  - [ ] Modal visible + Échap = ferme modal
  - [ ] Focus retourne au bouton déclencheur (pas au header)

- [ ] **Dropdowns**
  - [ ] Dropdown ouvert + Échap = ferme dropdown
  - [ ] Focus sur dropdown, pas disparu

- [ ] **Dialogs de confirmation**
  - [ ] Confirmation visible + Échap = annule (confirme comportement)

#### Flèches (↑ ↓ ← →)

- [ ] **Listes avec roving tabindex**
  - [ ] Première item = `tabindex="0"`
  - [ ] Autres items = `tabindex="-1"`
  - [ ] Flèche bas/droite = focus item suivant, tabindex update
  - [ ] Flèche haut/gauche = focus item précédent, tabindex update
  - [ ] Home = focus premier item
  - [ ] End = focus dernier item

- [ ] **Radiogroups**
  - [ ] Flèches navigent entre options radio
  - [ ] Option sélectionnée au clavier = cochée

- [ ] **Selectbox (si custom)**
  - [ ] Flèches bas/haut = navigateur options
  - [ ] Option en surbrillance (visuel)

#### Tabulation (Tab)

- [ ] **Shift+Tab backwards**
  - [ ] Tab au dernier champ + Shift+Tab = remonte
  - [ ] Ordre correct (reverse of Tab order)
  - [ ] Aucun élément sauté

- [ ] **Pas de Tab trap**
  - [ ] Page normale: Tab en dernier élément = focus header/skip link, pas boucle infinie
  - [ ] Modal ouverte: Tab en dernier élément = boucle dans modal seule
  - [ ] Modal fermée: Tab peut quitter modal, retour au background

- [ ] **Focus circulaire**
  - [ ] Tab au dernier élément → Tab = premier élément
  - [ ] Shift+Tab au premier → Shift+Tab = dernier élément

### 1.5 Workflows Clavier Complets

#### Workflow 1: Créer/Éditer Prompt

- [ ] Tab jusqu'à bouton "Nouveau prompt"
- [ ] Entrée = ouvre modal création
- [ ] Focus dans modal = premier champ (titre)
- [ ] Tab = titre → description → catégories → tags → bouton sauvegarder
- [ ] Shift+Tab = reverse order
- [ ] Bouton sauvegarder + Entrée = sauvegarde
- [ ] Modal ferme, focus retourne au bouton "Nouveau"

#### Workflow 2: Supprimer un Item

- [ ] Tab jusqu'à bouton "Supprimer" sur item
- [ ] Entrée = ouvre dialog confirmation
- [ ] Tab = "Annuler" → "Supprimer"
- [ ] Entrée sur "Supprimer" = supprime item
- [ ] Focus retourne à liste, item supprimé
- [ ] Page se met à jour sans reload

#### Workflow 3: Recherche et Filtrage

- [ ] Tab jusqu'à champ recherche
- [ ] Taper "test" = résultats filtrés
- [ ] Tab = champ recherche → filtre catégorie → filtre tag → résultats
- [ ] Flèches (si roving tabindex) = navigate résultats
- [ ] Entrée sur résultat = ouvre prompt

#### Workflow 4: Import/Export

- [ ] Tab = champ fichier → format export → bouton preview → bouton export
- [ ] Champ fichier:
  - [ ] Tab = focus sur input
  - [ ] Entrée = ouvre file picker
  - [ ] Sélectionner fichier = input rempli
- [ ] Select format = flèches changent format
- [ ] Bouton preview + Entrée = affiche aperçu dans modal
- [ ] Bouton export + Entrée = télécharge fichier

### 1.6 Problèmes Clavier - Checklist d'Issues

Pour chaque problème trouvé, noter:

- [ ] **URL/Page:** ******\_\_\_******
- [ ] **Élément affecté:** (ex: "Bouton sauvegarder dans modal création prompt")
- [ ] **Problème:**
  - [ ] Élément pas focusable (devrait l'être)
  - [ ] Élément focusable (ne devrait pas l'être)
  - [ ] Focus pas visible
  - [ ] Ordre Tab incorrect
  - [ ] Focus trap (impossible de quitter)
  - [ ] Touche non réactive (Entrée, Échap, etc.)
  - [ ] Flèches non réactives
- [ ] **Sévérité:**
  - [ ] Critique (bloque workflow)
  - [ ] Haute (rend difficile la navigation)
  - [ ] Moyenne (affecte expérience)
  - [ ] Basse (amélioration mineure)
- [ ] **Notes:** ******\_\_\_******

---

## Section 2: Audit Lecteurs d'Écran (T-ACC007)

### 2.1 Configuration de Test

#### NVDA (Windows)

- [ ] Télécharger NVDA gratuit (nvaccess.org)
- [ ] Installer version stable
- [ ] Lancer avec navigateur Firefox ou Chrome
- [ ] Mode de navigation: _Activer mode parcours_ (par défaut)
- [ ] Mode focus: Activer au Tab
- [ ] Commandes clés:
  - `Insert + H` = Aller au titre suivant
  - `H` = Titre suivant
  - `L` = Lien suivant
  - `B` = Bouton suivant
  - `F` = Formulaire suivant
  - `M` = Landmark suivant
  - `Insert + F7` = Liste de liens
  - `Insert + F5` = Liste de titres
  - `Insert + F6` = Liste d'éléments

#### VoiceOver (macOS)

- [ ] Activer: Préférences Système → Accessibilité → VoiceOver
- [ ] Commandes clés:
  - `VO + U` = Rotor Web (titres, liens, formulaires, etc.)
  - `VO + ↓` = Lire élément suivant
  - `VO + ↑` = Lire élément précédent
  - `VO + Space` = Activer élément
  - `VO + ← / →` = Navigate entre items
  - `VO + Cmd + Espace` = Rechercher sur page

### 2.2 Structure Page - Titres et Landmarks

#### Titres (Headings)

- [ ] **Page d'accueil**
  - [ ] H1 présent (ex: "PromptVault - Gérez vos prompts")
  - [ ] H2 pour sections (ex: "Prompts favoris", "Catégories")
  - [ ] Pas de sauts (H1 → H2, pas H1 → H3)
  - [ ] Hiérarchie logique

- [ ] **Autres pages (gestion, admin)**
  - [ ] H1 = titre page
  - [ ] H2 = sous-sections
  - [ ] Pas de sauts de niveau

- [ ] **Test NVDA:** `Insert + F5` = Liste titres
  - [ ] Tous les titres attendus présents
  - [ ] Ordre logique

#### Landmarks (Régions)

- [ ] **En haut:**
  - [ ] `<header>` ou `role="banner"` = logo + nav
  - [ ] `<nav>` ou `role="navigation"` = liens nav

- [ ] **Principal:**
  - [ ] `<main>` ou `role="main"` = contenu principal
  - [ ] ID unique `id="main-content"`

- [ ] **Latéral:**
  - [ ] `<aside>` ou `role="complementary"` si présent

- [ ] **Bas:**
  - [ ] `<footer>` ou `role="contentinfo"` = info footer

- [ ] **Test NVDA:** `M` = Landmark suivant
  - [ ] Parcourir tous les landmarks
  - [ ] Tous attendus présents

- [ ] **Test VoiceOver:** `VO + U` → sélectionner "Landmarks"
  - [ ] Tous landmarks listés
  - [ ] Peuvent être activés pour naviguer

### 2.3 Formulaires et Champs

#### Étiquettes (Labels)

- [ ] **Tous les inputs ont un label**
  - [ ] Text: "Nom d'utilisateur", "Email", "Mot de passe"
  - [ ] Checkbox: "J'accepte les conditions"
  - [ ] Radio: "Garder la session" / "Fermer la session"
  - [ ] Select: "Catégorie", "Format d'export"

- [ ] **Label correctement associé**
  - [ ] NVDA: Tab → champ → "Label Name, champ texte" (inclut le label)
  - [ ] VoiceOver: Sélectionner champ → titre = label

- [ ] **Aucun orphelin**
  - [ ] Aucun champ sans label/aria-label
  - [ ] Aucun label sans champ associé

#### Messages d'Erreur et Aide

- [ ] **Texte d'aide (aria-describedby)**
  - [ ] Champ mot de passe + help text: "Min. 12 caractères"
  - [ ] NVDA: Tab → champ → "Password, password, describedby: help text" (inclut aide)
  - [ ] VoiceOver: Sélectionner champ → description = inclut aide

- [ ] **Messages d'erreur**
  - [ ] Annoncés comme alertes (role="alert")
  - [ ] NVDA: Présence = "alert: Email invalide"
  - [ ] VoiceOver: "Alert: Email invalide"
  - [ ] Associés au champ via aria-describedby

- [ ] **Résumé d'erreurs**
  - [ ] Erreur formulaire = résumé en haut (aria-live="polite")
  - [ ] NVDA: Annonce automatique
  - [ ] VoiceOver: Focus sur résumé d'erreurs
  - [ ] Lien d'erreur → focus sur champ problématique

#### Soumission et Validation

- [ ] **Formulaires**
  - [ ] Bouton soumission nommé (ex: "Se connecter", "Sauvegarder")
  - [ ] NVDA: "Bouton: Se connecter" (bon)
  - [ ] Validation temps réel = annonce live region
  - [ ] Après soumission: redirection confirmée (page change annoncée)

### 2.4 Contenu Dynamique et Régions Live

#### Notifications (Toast, Alertes)

- [ ] **Affichage notification**
  - [ ] NVDA: Annonce automatique (aria-live="polite" ou "assertive")
  - [ ] VoiceOver: Annonce automatique

- [ ] **Exemples à tester:**
  - [ ] Prompt sauvegardé: "Prompt sauvegardé avec succès"
  - [ ] Erreur import: "Erreur: fichier invalide"
  - [ ] Action complétée: "3 prompts supprimés"

#### Mises à jour Liste

- [ ] **Filtrage**
  - [ ] Taper recherche = résultats mis à jour
  - [ ] NVDA: Annonce "X résultats trouvés"
  - [ ] VoiceOver: "X résultats trouvés"

- [ ] **Pagination**
  - [ ] Bouton "Suivant" = page suivante
  - [ ] Annonce "Page 2 de 10"

- [ ] **Tri**
  - [ ] Clic sur en-tête = tri
  - [ ] NVDA: "Triée croissant" ou "Triée décroissant"
  - [ ] VoiceOver: idem

### 2.5 Boutons et Contrôles

#### Noms Accessibles

- [ ] **Boutons avec icônes seules**
  - [ ] Bouton poubelle = aria-label="Supprimer"
  - [ ] NVDA: "Bouton: Supprimer"
  - [ ] Bouton cœur = aria-label="Ajouter aux favoris"
  - [ ] NVDA: "Bouton: Ajouter aux favoris"

- [ ] **Boutons avec texte**
  - [ ] NVDA: "Bouton: [Texte visible]"
  - [ ] Aucun bouton sans nom accessible

#### States (Activé, Désactivé, Appuyé)

- [ ] **Buttons disabled**
  - [ ] Bouton désactivé = aria-disabled="true" ou disabled
  - [ ] NVDA: "Bouton: [Nom], désactivé"
  - [ ] VoiceOver: "Disabled, [Nom] button"

- [ ] **Toggle buttons (favori, sélection)**
  - [ ] Appuyé = aria-pressed="true"
  - [ ] NVDA: "Bouton: Ajouter aux favoris, appuyé"
  - [ ] Non-appuyé = aria-pressed="false"
  - [ ] NVDA: "Bouton: Retirer des favoris"

### 2.6 Images et Icônes

#### Texte Alternatif

- [ ] **Images de contenu**
  - [ ] Logo = alt="PromptVault - Gérez vos prompts"
  - [ ] NVDA: Lit l'alt text

- [ ] **Icônes informatives**
  - [ ] Icône notification = aria-label="3 notifications"
  - [ ] NVDA: Annonce "3 notifications"

- [ ] **Icônes décoratives**
  - [ ] aria-hidden="true" + focusable="false"
  - [ ] NVDA: Pas annoncée

### 2.7 Modales et Dialogs

#### Ouverture

- [ ] **Modal visible**
  - [ ] role="dialog" ou role="alertdialog"
  - [ ] aria-modal="true"

- [ ] **Focus**
  - [ ] Ouverture = focus sur premier élément focusable (titre ou first button)
  - [ ] NVDA: Titre modal annoncé
  - [ ] VoiceOver: Focus visible dans modal

- [ ] **Aria-labelledby et aria-describedby**
  - [ ] aria-labelledby="modal-title" = titre modal annoncé
  - [ ] aria-describedby="modal-desc" = description annoncée

#### Navigation dans Modal

- [ ] **Tab**
  - [ ] Tab = focus prochain élément dans modal
  - [ ] Shift+Tab = focus élément précédent
  - [ ] Aucun saut hors modal

- [ ] **Fermeture**
  - [ ] Échap = ferme modal
  - [ ] Focus retour = bouton qui a ouvert modal
  - [ ] NVDA: Annonce "Modal fermée"

### 2.8 Navigation et Roving Tabindex

#### Listes avec Roving Tabindex

- [ ] **Première liste (catégories ou tags)**
  - [ ] Tab = premier item focusable seule (tabindex="0")
  - [ ] Autres items = tabindex="-1"
  - [ ] Flèches = navigate entre items
  - [ ] NVDA: "Elément 1 de 10"

- [ ] **Annonces**
  - [ ] Flèche bas = "Elément 2 de 10, [Nom item]"
  - [ ] Home = "Elément 1 de 10"
  - [ ] End = "Elément 10 de 10"

### 2.9 Workflows Complets Lecteurs d'Écran

#### Workflow 1: Créer Prompt (VoiceOver macOS)

- [ ] Activer VoiceOver
- [ ] `VO + U` → Rotor → Boutons → "Nouveau prompt"
- [ ] `VO + Space` = ouvre modal
- [ ] Modal titre annoncé = "Créer nouveau prompt"
- [ ] `VO + ↓` = "Titre, text field"
- [ ] Taper titre
- [ ] `VO + ↓` = "Description, text field"
- [ ] Taper description
- [ ] `VO + ↓` = "Catégories, groupbox"
- [ ] Sélectionner catégories
- [ ] `VO + ↓` = "Bouton: Sauvegarder"
- [ ] `VO + Space` = sauvegarde
- [ ] Modal ferme, retour au bouton "Nouveau"

#### Workflow 2: Filtrer Prompts (NVDA Windows)

- [ ] NVDA actif
- [ ] `Insert + F5` = Liste titres
- [ ] Sélectionner "Rechercher"
- [ ] `Entrée` = focus sur champ recherche
- [ ] Taper "javascript"
- [ ] Résultats mis à jour
- [ ] NVDA annonce: "10 prompts trouvés"
- [ ] `Insert + F7` = Liste de liens
- [ ] Sélectionner premier prompt
- [ ] `Entrée` = ouvre prompt

### 2.10 Problèmes Lecteurs d'Écran - Checklist d'Issues

Pour chaque problème trouvé, noter:

- [ ] **URL/Page:** ******\_\_\_******
- [ ] **Lecteur d'écran:** NVDA / VoiceOver
- [ ] **Élément affecté:** (ex: "Bouton suppression dans modal confirmation")
- [ ] **Problème:**
  - [ ] Élément pas annoncé
  - [ ] Élément mal nommé (nom incorrect ou absent)
  - [ ] Role manquant (dialog, alert, live region, etc.)
  - [ ] Description manquante (aria-describedby)
  - [ ] État non annoncé (disabled, pressed, etc.)
  - [ ] Titre/landmark manquant
  - [ ] Alt text manquant/incorrect
  - [ ] Live region non annoncée
  - [ ] Ordre logique incorrect
- [ ] **Sévérité:**
  - [ ] Critique (bloque accès)
  - [ ] Haute (rend incompréhensible)
  - [ ] Moyenne (affecte compréhension)
  - [ ] Basse (amélioration)
- [ ] **Notes:** ******\_\_\_******

---

## Matrice de Test Résumée

| Page                 | Clavier | VoiceOver | NVDA | Statut |
| -------------------- | ------- | --------- | ---- | ------ |
| `/`                  | [ ]     | [ ]       | [ ]  |        |
| `/auth/login`        | [ ]     | [ ]       | [ ]  |        |
| `/auth/register`     | [ ]     | [ ]       | [ ]  |        |
| `/backup-management` | [ ]     | [ ]       | [ ]  |        |
| `/import-export`     | [ ]     | [ ]       | [ ]  |        |
| `/manage-categories` | [ ]     | [ ]       | [ ]  |        |
| `/manage-tags`       | [ ]     | [ ]       | [ ]  |        |
| `/admin/users`       | [ ]     | [ ]       | [ ]  |        |
| `/admin/sessions`    | [ ]     | [ ]       | [ ]  |        |
| `/profile`           | [ ]     | [ ]       | [ ]  |        |

---

## Notes Importantes

1. **Environnement de test:** Tester sur `http://127.0.0.1:8003` avec compte test authentifié
2. **Navigateurs:** Firefox + Chrome
3. **Systèmes:** Windows (NVDA) + macOS (VoiceOver) si possible
4. **Enregistrement:** Noter tous les problèmes dans les issues GitHub avec tag `a11y`
5. **Priorité:** Tester d'abord workflows critiques (création, suppression, navigation)
6. **Temps estimé:** 3-4 heures par auditeur, par lecteur d'écran
