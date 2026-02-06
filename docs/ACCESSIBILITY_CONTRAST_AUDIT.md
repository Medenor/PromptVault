# Audit Contraste et Indicateurs Hors Couleur (T-ACC026 / T-ACC027)

Ce document structure l'audit contraste complet (texte + composants) et aide a transformer les constats en corrections actionnables.

## Rappel WCAG 2.1 AA

- Texte normal: ratio >= 4.5:1
- Grand texte (18px+ ou 14px+ gras): ratio >= 3:1
- Composants UI et etats (bordures, icones informatives, focus): ratio >= 3:1 contre l'arriere-plan adjacent
- Ne pas transmettre une info uniquement par la couleur (ajouter texte, icone, forme, motif, etc.)

## Outils

- WebAIM Contrast Checker
- DevTools (inspector: couleurs calculees)
- axe DevTools / Playwright + axe (verifie aussi `color-contrast`, mais ne remplace pas l'audit complet)

## Zones a auditer en priorite

- Textes secondaires (`text-gray-*`, aide de champ, placeholders)
- Etats disabled (texte + bordure)
- Boutons secondaires sur fonds colores (header blue)
- Badges, chips, etiquettes
- Bordures de tableaux et separateurs
- Focus ring et etats hover/active
- Liens dans le contenu (`main`) et dans les zones colorees

## Procedure (par page)

1. Identifier les fonds dominants (ex: `bg-white`, `bg-gray-50`, header `bg-blue-500`).
2. Mesurer:
   - Texte principal
   - Texte secondaire / descriptions
   - Placeholders (si utilises comme information)
   - Boutons (texte + fond)
   - Etats (warning/success/error)
3. Verifier les etats:
   - normal, hover, focus-visible, disabled
4. Noter chaque probleme dans la table ci-dessous.

## Table de suivi

- `[ ]` Page:
- `[ ]` Selecteur CSS (ou description):
- `[ ]` Texte/composant concerne:
- `[ ]` Couleur texte/icone/bordure:
- `[ ]` Couleur fond adjacent:
- `[ ]` Ratio mesure:
- `[ ]` Seuil attendu:
- `[ ]` Fix propose (token Tailwind / variable / composant):

## Indicateurs hors couleur

Points a verifier systematiquement:

- `[ ]` Erreurs: texte explicite + icone (si pertinent) + role/aria-live
- `[ ]` Warning: texte explicite + icone + style distinct
- `[ ]` Success: texte explicite + icone + style distinct
- `[ ]` Favoris: icone + `aria-pressed` + label (deja traite)
- `[ ]` Liens: pas uniquement la couleur (deja traite dans `main`)

