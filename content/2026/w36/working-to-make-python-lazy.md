---
title: Working to make Python lazy
url_link: https://iscinumpy.dev/post/flake8-lazy/
tags:
- python
- ai
description: 'Python 3.15a7, which is now just a uv python install 3.15 away on all
  major platforms, has lazy imports! This exciting feature, proposed in PEP 810, promises
  to make CLI applications faster (especially when using flags like --help), and could
  make a lot of large code with lots of imports that don’t always get used faster
  too. Unlike the earlier, failed attempt, this requires libraries to put in some
  work. I’ve developed a helper tool to make it easy; I’d like to cover what lazy
  imports are and how to use my tool. Since this is the first library that I used
  AI heavily in developing, the second half of the post will cover how my experience
  with AI for a task like this went.

  TL;DR: run uvx flake8-lazy --apply=list to make your code magically faster on Python
  3.15!'
date: '2026-09-04'
year: 2026
week: 36
comments: []
---
