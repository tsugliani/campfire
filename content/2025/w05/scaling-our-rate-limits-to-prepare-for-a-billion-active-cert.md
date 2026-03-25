---
title: Scaling Our Rate Limits to Prepare for a Billion Active Certificates
url_link: https://letsencrypt.org/2025/01/30/scaling-rate-limits/
tags:
- rate
- redis
- gcra
- scalability
description: 'Let’s Encrypt protects a vast portion of the Web by providing TLS certificates
  to over 550 million websites—a figure that has grown by 42% in the last year alone.
  We currently issue over 340,000 certificates per hour. To manage this immense traffic
  and maintain responsiveness under high demand, our infrastructure relies on rate
  limiting. In 2015, we introduced our first rate limiting system, built on MariaDB.
  It evolved alongside our rapidly growing service but eventually revealed its limits:
  straining database servers, forcing long reset times on subscribers, and slowing
  down every request.

  '
date: '2025-01-30'
year: 2025
week: 5
comments: []
---
