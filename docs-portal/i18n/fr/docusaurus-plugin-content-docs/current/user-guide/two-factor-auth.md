---
title: Authentification à deux facteurs
sidebar_position: 5
---

# Authentification à deux facteurs

L'authentification à deux facteurs (2FA) ajoute une vérification lors de la connexion. Après votre mot de passe, PromptVault demande un code à 6 chiffres provenant d'une application d'authentification, ou l'un de vos codes de récupération. La 2FA est facultative pour la plupart des utilisateurs. Les administrateurs peuvent l'exiger pour certains rôles.

## Activer la 2FA {#enabling-2fa}

1. Ouvrez votre profil et repérez la carte **Authentification à deux facteurs**. Sélectionnez **Configurer l'authentification à deux facteurs**.
2. Scannez le code QR avec une application d'authentification, comme Google Authenticator, Authy ou 1Password. Si vous ne pouvez pas le scanner, ouvrez **Impossible de scanner le code ?** et saisissez à la main la **clé de configuration** dans l'application.
3. Saisissez le code à 6 chiffres affiché dans votre application, puis sélectionnez **Vérifier et activer**.
4. Conservez vos codes de récupération. PromptVault ne les affiche qu'une seule fois : 10 codes. Copiez-les ou téléchargez-les dans un fichier texte, et rangez-les en lieu sûr.

La 2FA n'est active qu'après l'étape 3. Si vous recommencez la configuration avant de la confirmer, la nouvelle clé de configuration remplace l'ancienne.

## Se connecter avec la 2FA {#signing-in-with-2fa}

1. Saisissez votre mot de passe comme d'habitude.
2. Sur l'écran **Authentification à deux facteurs**, saisissez le code à 6 chiffres de votre application, puis sélectionnez **Vérifier**.

L'étape de connexion expire au bout de 2 minutes. Si elle expire, recommencez depuis l'étape du mot de passe.

Les codes de l'application changent toutes les 30 secondes. Un code fonctionne aussi une étape avant ou après l'heure actuelle : une horloge de téléphone légèrement décalée reste donc utilisable.

## Se connecter avec un code de récupération {#signing-in-with-a-recovery-code}

Sur le même écran, saisissez un code de récupération à la place du code de l'application. Les codes de récupération ressemblent à `xxxx-xxxx`. Chaque code ne fonctionne qu'une fois. Une fois utilisé, il ne fonctionne plus jamais.

Utilisez un code de récupération pour revenir si vous perdez votre téléphone. Régénérez ensuite vos codes.

## Régénérer les codes de récupération {#regenerating-recovery-codes}

Depuis votre profil, sélectionnez **Régénérer les codes de récupération**. Saisissez votre mot de passe actuel et un code actuel de l'application ou un code de récupération. PromptVault crée 10 nouveaux codes. Tous les codes précédents cessent aussitôt de fonctionner.

## Désactiver la 2FA {#disabling-2fa}

Depuis votre profil, sélectionnez **Désactiver l'authentification à deux facteurs**. Saisissez votre mot de passe actuel et un code actuel de l'application ou un code de récupération. La désactivation supprime votre configuration 2FA et tous les codes de récupération restants. Ensuite, vous vous connectez avec votre seul mot de passe.

## Exiger la 2FA pour un rôle {#requiring-2fa-for-a-role}

Dans la section **Politique d'authentification à deux facteurs** de l'administration, choisissez les rôles (lecteur, éditeur, administrateur) qui doivent utiliser la 2FA. Un changement s'applique à la prochaine connexion de chaque utilisateur. Il ne met pas fin aux sessions existantes.

- Un utilisateur d'un rôle obligatoire qui n'a pas configuré la 2FA est dirigé vers une étape de configuration juste après sa connexion. Il ne peut pas utiliser le reste de l'application tant que la configuration n'est pas terminée.
- Un utilisateur d'un rôle obligatoire qui a déjà la 2FA se connecte avec l'étape de code habituelle.
- Retirer une exigence ne supprime la configuration 2FA existante de personne.

## Si vous perdez votre application et vos codes de récupération {#if-you-lose-your-authenticator-and-recovery-codes}

PromptVault ne peut pas réinitialiser la 2FA pour vous dans ce cas. À ce jour, aucune option d'administration ne retire la 2FA d'un compte. Contactez la personne qui administre votre serveur PromptVault, et conservez vos codes de récupération en lieu sûr pour ne jamais vous retrouver dans cette situation.

## Notes de sécurité {#security-notes}

- Votre configuration 2FA est stockée chiffrée. Les codes de récupération sont stockés sous une forme qui ne permet pas de les relire : ils ne peuvent donc plus être affichés.
- Les mauvais codes comptent pour le même verrouillage que les mauvais mots de passe. Trop de tentatives erronées verrouillent le compte pendant un court moment.
- Le journal d'audit enregistre l'activation ou la désactivation de la 2FA, la régénération des codes de récupération et les changements d'exigence d'un rôle.
- PromptVault limite le nombre de tentatives de configuration, de vérification, de désactivation et de régénération. Si un message indique un trop grand nombre de tentatives, attendez une minute, puis réessayez.
- L'opérateur du serveur doit définir `TOTP_ENCRYPTION_KEY`. Voir [Configuration](../configuration/index.md).
