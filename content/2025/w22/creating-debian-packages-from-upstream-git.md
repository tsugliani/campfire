---
title: Creating Debian packages from upstream Git
url_link: https://optimizedbyotto.com/post/debian-packaging-from-git/
tags:
- git
- debian
- packaging
- upstream
description: In this post, I demonstrate the optimal workflow for creating new Debian
  packages in 2025, preserving the upstream Git history. The motivation for this is
  to lower the barrier for sharing improvements to and from upstream, and to improve
  software provenance and supply-chain security by making it easy to inspect every
  change at any level using standard Git tooling.\nKey elements of this workflow include:\nUsing
  a Git fork/clone of the upstream repository as the starting point for creating Debian
  packaging repositories. Consistent use of the same git-buildpackage commands, with
  all package-specific options in gbp.conf. DEP-14 tag and branch names for an optimal
  Git packaging repository structure. Pristine-tar and upstream signatures for supply-chain
  security. Use of Files-Excluded in the debian/copyright file to filter out unwanted
  files in Debian. Patch queues to easily rebase and cherry-pick changes across Debian
  and upstream branches. Efficient use of Salsa, Debian’s GitLab instance, for both
  automated feedback from CI systems and human feedback from peer reviews. To make
  the instructions so concrete that anyone can repeat all the steps themselves on
  a real package, I demonstrate the steps by packaging the command-line tool Entr.
  It is written in C, has very few dependencies, and its final Debian source package
  structure is simple, yet exemplifies all the important parts that go into a complete
  Debian package:\n
date: '2025-05-26'
year: 2025
week: 22
comments: []
---
