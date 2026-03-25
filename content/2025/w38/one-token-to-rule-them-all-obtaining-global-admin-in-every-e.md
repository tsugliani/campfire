---
title: One Token to rule them all - obtaining Global Admin in every Entra ID tenant
  via Actor tokens
url_link: https://dirkjanm.io/obtaining-global-admin-in-every-entra-id-tenant-with-actor-tokens/
tags:
- security
- api
- azure
- entradirectory
description: 'While preparing for my Black Hat and DEF CON talks in July of this year,
  I found the most impactful Entra ID vulnerability that I will probably ever find.
  One that could have allowed me to compromise every Entra ID tenant in the world
  (except probably those in national cloud deployments). If you are an Entra ID admin
  reading this, yes that means complete access to your tenant. The vulnerability consisted
  of two components: undocumented impersonation tokens that Microsoft uses in their
  backend for service-to-service (S2S) communication, called “Actor tokens”, and a
  critical vulnerability in the (legacy) Azure AD Graph API that did not properly
  validate the originating tenant, allowing these tokens to be used for cross-tenant
  access.'
date: '2025-09-17'
year: 2025
week: 38
comments: []
---
