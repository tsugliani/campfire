---
title: Making HTTP requests from a container that has no curl, using bash /dev/tcp
url_link: https://mareksuppa.com/til/bash-dev-tcp-http-without-curl/
tags:
- docker
- containers
- networking
- troubleshooting
description: Minimal container images often ship without curl, wget, or any HTTP client
  at all. Bash can open a TCP socket through /dev/tcp, which is enough to write a
  tiny HTTP/1.1 request by hand for quick checks.
date: '2026-06-18'
year: 2026
week: 25
comments: []
---
