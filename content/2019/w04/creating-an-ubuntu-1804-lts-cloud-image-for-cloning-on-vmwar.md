---
title: Creating an Ubuntu 18.04 LTS cloud image for cloning on VMware
url_link: https://blah.cloud/kubernetes/creating-an-ubuntu-18-04-lts-cloud-image-for-cloning-on-vmware/
tags:
- cloud
- infrastructure
- networking
- storage
- automation
description: 'Intro

  I have been experimenting a lot over the past 18 months with containers and in particular,
  Kubernetes, and one of the core things I always seemed to get hung up on was part-zero
  - creating the VMs to actually run K8s. I wanted a CLI only way to build a VM template
  for the OS and then deploy that to the cluster.

  It turns out that with Ubuntu 18.04 LTS (in particular the cloud image OVA) there
  are a few things need changed from the base install (namely cloud-init) in order
  to make them play nice with OS Guest Customisation in vCenter.'
date: '2019-01-27'
year: 2019
week: 4
comments: []
---


