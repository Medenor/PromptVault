---
title: Authentification à deux facteurs
sidebar_position: 5
---

# Authentification à deux facteurs

## État actuel

L'authentification à deux facteurs par mot de passe à usage unique basé sur le temps (TOTP) n'est **pas encore disponible** dans PromptVault. Il s'agit d'un renforcement prévu du système d'authentification, suivi sur la feuille de route du projet, mais aucun flux d'inscription, aucune étape de vérification à la connexion, ni aucune politique d'application côté administrateur n'existe dans l'application aujourd'hui.

## Ce qui est déjà en place

Bien que la 2FA dédiée ne soit pas encore disponible, la pile d'authentification de PromptVault inclut déjà plusieurs niveaux de protection sur votre compte :

- **Hachage de mot de passe robuste** (Argon2id) avec une politique de mot de passe appliquée (longueur minimale et exigences de classes de caractères).
- **Verrouillage de compte** après des tentatives de connexion échouées répétées, pour une durée configurable.
- **Jetons JWT d'accès/rafraîchissement à courte durée de vie et rotatifs**, avec détection de réutilisation — un jeton de rafraîchissement volé ne peut pas être rejoué indéfiniment.
- **Une limite du nombre de sessions simultanées par compte**, avec suivi de l'appareil/IP et possibilité de révoquer toute session active.
- **Un flux de réinitialisation de mot de passe sans énumération** — les demandes de réinitialisation ne révèlent jamais si une adresse e-mail est associée à un compte.

Voir `docs/AUTHENTICATION_SECURITY.md` du projet pour le détail complet de ces contrôles.

## Conception prévue

La feuille de route décrit la 2FA TOTP comme une inscription facultative (code QR + secret, avec codes de récupération à usage unique) qui insère une étape de vérification à la connexion une fois activée pour un compte, plus une politique d'administration pour la rendre obligatoire pour des rôles spécifiques. Les tentatives de vérification seraient limitées en débit, et les événements d'inscription/désactivation/vérification seraient journalisés à des fins d'audit, cohérent avec la façon dont les autres actions sensibles à la sécurité sont déjà journalisées aujourd'hui dans PromptVault.

## Recommandation en attendant

Si votre déploiement a besoin d'une protection plus forte qu'un simple mot de passe dès aujourd'hui, les options pratiques sont : conserver `AUTH_ENABLED=true` (ne jamais exécuter une instance multi-utilisateur en réseau avec l'authentification désactivée), appliquer une politique de mot de passe robuste via les variables d'environnement `PASSWORD_*`, et s'appuyer sur la limite de sessions et les contrôles de révocation existants pour limiter l'impact d'un identifiant compromis. Cette page sera mise à jour dès que le support TOTP sera disponible.
