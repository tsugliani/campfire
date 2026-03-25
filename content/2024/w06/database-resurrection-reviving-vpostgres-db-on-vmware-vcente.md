---
title: Database Resurrection - Reviving vPostgres DB on VMware vCenter Server
url_link: https://rguske.github.io/post/database-resurrection-reviving-postgres-on-vmware-vcenter/
tags:
- database
- virtualization
description: The VCSA vPostgres service fails starting. In this post I describe how
  I was able to revive my Postgres instance with the help of the Postgres Write-Ahead
  log (WAL). The Postgres Write-Ahead Log contains enough data for Postgres to restore
  its state to the last committed transaction. Nevertheless, this action should be
  done with care.
date: '2024-02-07'
year: 2024
week: 6
comments: []
---


