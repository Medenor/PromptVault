# Audit Manuel Accessibilite (T-ACC006 / T-ACC007)

Ce document sert de "feuille de route" pour les audits manuels clavier et lecteurs d'ecran. Il est concu pour etre rempli au fil des tests, afin de transformer l'audit en liste d'actions precise.

## Portee

Routes a auditer (minimum):

- `/`
- `/import-export`
- `/backup-management`
- `/auth/login`
- `/auth/register`
- `/auth/forgot-password`
- `/auth/reset-password?token=test`
- `/auth/profile`
- `/manage-categories`
- `/manage-tags`
- `/admin/users`
- `/admin/sessions`

Contexte:

- Desktop: Chrome/Chromium et Firefox (au moins 1)
- Mobile: Safari iOS ou Chrome Android (si possible)
- Clavier: tabulation, fleches, Entree, Echap, Home/End

## T-ACC006: Audit Clavier (manuel)

### Checklist "page" (a repeter sur chaque route)

- `[ ]` Skip link visible au focus et amene bien au contenu principal (`#main-content`)
- `[ ]` Ordre de tabulation logique (pas de sauts "surprenants")
- `[ ]` Aucun "trap" clavier (impossible de sortir d'un composant)
- `[ ]` Focus toujours visible (contraste et epaisseur suffisants)
- `[ ]` Tous les controles activables au clavier (Entree/Espace selon le type)
- `[ ]` Echap ferme les modales/menus ouverts et rend le focus au declencheur
- `[ ]` Les elements desactives ne sont pas focusables
- `[ ]` Le focus n'atterrit pas sur des icones decoratives

### Checklist "composants"

- Filtres categories/tags (roving tabindex):
- `[ ]` Fleches: deplacer le focus dans la liste
- `[ ]` Home/End: premier/dernier element
- `[ ]` Activation: Entree/Espace sur l'element focalise
- `[ ]` Typeahead: taper une lettre saute au prochain element correspondant

- Tableaux admin (/admin/users, /admin/sessions):
- `[ ]` Navigation au clavier possible sans perdre le focus
- `[ ]` Les actions par ligne sont accessibles (boutons/lien)
- `[ ]` Typeahead (premiere lettre) fonctionne sur les lignes si implemente (T-ACC019)

### Notes de capture

Pour chaque probleme, consigner:

- Route:
- Etapes pour reproduire:
- Attendu:
- Observe:
- Severite (bloquant / genant / mineur):
- Suggestion de correction:

## T-ACC007: Audit Lecteurs d'Ecran (manuel)

Lecteurs d'ecran recommandes:

- macOS: VoiceOver (Chrome et Safari)
- Windows: NVDA (Firefox)

### Checklist "annonces et structure"

- `[ ]` La page annonce un titre pertinent (h1)
- `[ ]` Landmarks utilisables (banner/nav/main/footer si present)
- `[ ]` Les boutons et liens ont un nom accessible pertinent
- `[ ]` Les champs ont label + aide/erreur annoncees (aria-describedby)
- `[ ]` Les erreurs (banniere + champs) sont annoncees, et le lien amenant au champ fonctionne
- `[ ]` Les notifications success/warning/error sont annoncees a un niveau approprie (status vs alert)

### Scenarios critiques

- Auth:
- `[ ]` Login: erreur d'identifiants annoncee, focus correctement replace
- `[ ]` Reset password: champs + aide + validation annonces

- Import/Export et Backup:
- `[ ]` Progres/etat annonce (si zone dynamique)
- `[ ]` Les dialogues de confirmation ne bloquent pas le lecteur d'ecran

- Admin:
- `[ ]` Tables: entetes et cellules lisibles, actions identifiables

