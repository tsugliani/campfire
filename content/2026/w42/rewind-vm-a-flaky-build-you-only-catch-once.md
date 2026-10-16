---
title: 'Rewind VM: a flaky build you only catch once'
url_link: https://fzakaria.com/2026/10/03/rewind-vm-a-flaky-build-you-only-catch-once
tags:
- virtualization
- testing
- troubleshooting
- linux
description: If a test fails on CI and nobody can reproduce it, did it really fail?
  🧘 Nix gives me a build that is a function of its inputs via the extensional model.
  The same derivation, produces the same store path, and if I am lucky, the same bytes.
  What Nix does not give me is the same run.1 A test suite with a race in it may pass
  on my laptop, fail once on CI, and when I rebuild it to look, it passes again. A
  run is the sequence of events that happen in a process to produce a…
date: '2026-10-16'
year: 2026
week: 42
comments: []
---
