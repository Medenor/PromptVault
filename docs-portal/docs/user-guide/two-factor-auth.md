---
title: Two-Factor Authentication
sidebar_position: 5
---

# Two-Factor Authentication

Two-factor authentication (2FA) adds a second check when you sign in. After your password, PromptVault asks for a 6-digit code from an authenticator app, or for one of your recovery codes. 2FA is optional for most users. Administrators can require it for specific roles.

## Enabling 2FA {#enabling-2fa}

1. Open your profile and find the **Two-Factor Authentication** card. Select **Set up two-factor authentication**.
2. Scan the QR code with an authenticator app such as Google Authenticator, Authy, or 1Password. If you can't scan it, expand **Can't scan the code?** and type the **setup key** into the app by hand.
3. Enter the 6-digit code shown in your app, then select **Verify and enable**.
4. Save your recovery codes. PromptVault shows 10 codes only once. Copy them or download them as a text file, and store them somewhere safe.

2FA is not active until you complete step 3. If you start setup again before confirming, the new setup key replaces the old one.

## Signing In With 2FA {#signing-in-with-2fa}

1. Enter your password as usual.
2. On the **Two-factor authentication** screen, enter the 6-digit code from your app and select **Verify**.

The sign-in step expires after 2 minutes. If it expires, start again from the password step.

App codes change every 30 seconds. A code also works one step before or after the current time, so a phone clock that is a little out of sync still works.

## Signing In With a Recovery Code {#signing-in-with-a-recovery-code}

On the same screen, enter a recovery code instead of the app code. Recovery codes look like `xxxx-xxxx`. Each code works once. After you use it, it stops working for good.

Use a recovery code to get back in if you lose your phone. Then regenerate your codes.

## Regenerating Recovery Codes {#regenerating-recovery-codes}

From your profile, select **Regenerate recovery codes**. Enter your current password and a current app code or recovery code. PromptVault creates 10 new codes. Every earlier code stops working at once.

## Disabling 2FA {#disabling-2fa}

From your profile, select **Disable two-factor authentication**. Enter your current password and a current app code or recovery code. Disabling removes your 2FA setup and all remaining recovery codes. After that, you sign in with your password alone.

## Requiring 2FA for a Role {#requiring-2fa-for-a-role}

In the admin **Two-Factor Authentication Policy** section, choose which roles (viewer, editor, admin) must use 2FA. A change applies at each user's next sign-in. It does not end existing sessions.

- A user in a required role who has not set up 2FA is taken to a setup step right after signing in. They cannot use the rest of the application until setup is complete.
- A user in a required role who already has 2FA signs in with the normal code step.
- Removing a requirement does not remove anyone's existing 2FA setup.

## If You Lose Your Authenticator and Recovery Codes {#if-you-lose-your-authenticator-and-recovery-codes}

PromptVault cannot reset 2FA for you in this case. Today, no administrator option removes 2FA from an account. Contact the person who runs your PromptVault server, and keep your recovery codes somewhere safe so you never reach this point.

## Security Notes {#security-notes}

- Your 2FA setup is stored encrypted. Recovery codes are stored in a form that cannot be read back, so they cannot be shown again.
- Wrong codes count toward the same lock as wrong passwords. Too many wrong attempts lock the account for a short time.
- The audit log records enabling or disabling 2FA, regenerating recovery codes, and changes to a role's requirement.
- PromptVault limits how often setup, verification, disabling, and regeneration can be tried. If you see a message about too many attempts, wait a minute and try again.
- The server operator must set `TOTP_ENCRYPTION_KEY`. See [Configuration](../configuration/index.md).
