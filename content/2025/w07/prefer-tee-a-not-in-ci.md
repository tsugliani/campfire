---
title: Prefer tee -a, not >>, in CI
url_link: https://huonw.github.io/blog/2025/02/ci-tee/
tags:
- ci
- shell
- github
- automation
description: GitHub Actions suggests using code like echo ... >> $GITHUB_ENV, but
  echo ... | tee -a $GITHUB_ENV is often better.
date: '2025-02-13'
year: 2025
week: 7
comments: []
---
