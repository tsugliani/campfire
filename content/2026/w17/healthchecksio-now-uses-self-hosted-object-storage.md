---
title: Healthchecks.io Now Uses Self-hosted Object Storage
url_link: https://blog.healthchecks.io/2026/04/healthchecks-io-now-uses-self-hosted-object-storage/
tags:
- storage
- s3
- postgresql
- selfhosted
description: Healthchecks.io ping endpoints accept HTTP HEAD, GET, and POST request
  methods. When using HTTP POST, clients can include an arbitrary payload in the request
  body. Healthchecks.io stores the first 100kB of the request body. If the request
  body is tiny, Healthchecks.io stores it in the PostgreSQL database. Otherwise, it
  stores it in S3-compatible object storage. [...]
date: '2026-04-21'
year: 2026
week: 17
comments: []
---
