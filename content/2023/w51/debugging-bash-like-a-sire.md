---
title: Debugging Bash like a Sire
url_link: https://blog.brujordet.no/post/bash/debugging_bash_like_a_sire/
tags:
- cli
- terminal
- automation
description: 'Many engineers have a strained relationship with Bash. I love it though,
  but I’m very aware of it’s limitations when it comes to error handling and data
  structures (or lack thereof).

  As a result of these limitations I often see Bash scripts written very defensively
  that define something like:

  set -euxo pipefail These are bash builtin options that do more or less sensible
  things.

  e: Exit immediately when a non-zero exit status is encountered u: Undefined variables
  throws an error and exits the script x: Print every evaluation. o pipefail: Here
  we make sure that any error in a pipe of commands will fail the entire pipe instead
  just carrying on to the next command in the pipe. All of these are quite useful,
  thought I tend to skip the -u flag as bash scripts often interact with global variables
  that are set outside my scripts. The -x flag is extremely noisy so it’s most often
  used manually when debugging. And to be honest, I don’t really use -o pipefail either.
  I guess this is a good place for a few words of caution when it comes to this approach.
  Feel free to dig into this reddit comment, but to summarize, the behavior of these
  flags aren’t consistent across Bash versions and they can break your scripts in
  unexpected ways.'
date: '2023-12-23'
year: 2023
week: 51
comments: []
---


