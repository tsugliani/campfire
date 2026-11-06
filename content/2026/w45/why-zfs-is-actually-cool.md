---
title: Why ZFS is actually cool
url_link: https://blog.dfb.sh/blog/zfs-fsync/
tags:
- storage
- linux
- homelab
- performance
description: 'fsync promises two things, durability and ordering, and I only need
  ordering. ext4 gives both or neither: every fsync commits the journal and flushes
  the disk cache. ZFS with sync=disabled gives ordering alone: transaction groups
  land in order, and a crash loses the last tens of seconds, not a database. My two
  HDDs are 2.7% busy instead of 13%, and a write takes 2 ms instead of 16.'
date: '2026-11-06'
year: 2026
week: 45
comments: []
---
