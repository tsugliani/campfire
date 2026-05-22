---
title: What's new in Proxmox VE 9.2
url_link: https://www.youtube.com/watch?v=XBVAiwkVaqA
tags:
- proxmox
- virtualization
- networking
- storage
description: 'This video highlights the key features introduced in Proxmox Virtual
  Environment 9.2. The release debuts a Dynamic Load Balancer for real-time cluster
  resource scheduling and automated high-availability (HA) migrations. Networking
  receives an enterprise overhaul with native WireGuard and BGP fabrics for secure
  cross-site inter-node connections, alongside granular Route Maps and Prefix Lists
  for advanced BGP/EVPN route filtering.


  Chapters

  <a href="https://www.youtube.com/watch?v=XBVAiwkVaqA&t=0s" target="_blank" rel="noopener">0:00</a>
  - Introduction to Proxmox VE 9.2  (Stable: May 21, 2026)

  <a href="https://www.youtube.com/watch?v=XBVAiwkVaqA&t=2s" target="_blank" rel="noopener">0:02</a>
  - Dynamic Load Balancer

  <a href="https://www.youtube.com/watch?v=XBVAiwkVaqA&t=53s" target="_blank" rel="noopener">0:53</a>
  - Disarm/Arm maintenance workflow

  <a href="https://www.youtube.com/watch?v=XBVAiwkVaqA&t=95s" target="_blank" rel="noopener">1:35</a>
  - Custom CPU models

  <a href="https://www.youtube.com/watch?v=XBVAiwkVaqA&t=135s" target="_blank" rel="noopener">2:15</a>
  - WireGuard Fabric for SDN

  <a href="https://www.youtube.com/watch?v=XBVAiwkVaqA&t=189s" target="_blank" rel="noopener">3:09</a>
  - Route Maps & Prefix Lists

  <a href="https://www.youtube.com/watch?v=XBVAiwkVaqA&t=264s" target="_blank" rel="noopener">4:24</a>
  - Ceph Tentacle 20.2

  <a href="https://www.youtube.com/watch?v=XBVAiwkVaqA&t=283s" target="_blank" rel="noopener">4:43</a>
  - Updates & Repositories Check: Debian 13.5 & Kernel 7.0


  What you will learn?

  ▪ Cluster resource scheduling: How the new dynamic load balancer evaluates real-time
  node utilization to eliminate cluster resource imbalances automatically.

  ▪ HA maintenance windows: Utilizing the new "Disarm and Arm" workflow to safely
  freeze or ignore HA constraints during node maintenance.

  ▪ Custom CPU models: Managing cluster-wide custom CPU models and validating processor
  flags directly via the web UI to prevent migration compatibility issues.

  ▪ WireGuard & BGP mesh: Deploying a secure mesh network for encrypted inter-node
  traffic across untrusted network segments.

  ▪ Route Maps, Prefix Lists: Building complex network topologies using Route Maps,
  Prefix Lists  for fine-grained BGP and EVPN route filtering.

  ▪ Ceph Tentacle 20.2 integration: Initializing new cluster nodes with the new default
  Ceph version via the web interface or CLI.


  [DATA SNAPSHOT] Proxmox VE 9.2 (Stable: May 21, 2026)

  Base OS: Debian 13.5 "Trixie" | Default Kernel: Linux Kernel 7.0

  Core components: Ceph Tentacle 20.2, QEMU 11, LXC 7, ZFS 2.4

  Key network tech: WireGuard Fabric, BGP Fabric, EVPN SLAAC, Route Maps, Prefix Lists

  Official Release Notes: https://pve.proxmox.com/wiki/Roadmap


  Technical Q&A

  Q: How does the Proxmox VE 9.2 dynamic load balancer migrate workloads?

  A: It continuously evaluates real-time CPU and memory utilization across cluster
  nodes. When an imbalance is detected, it automatically migrates HA managed guests
  live without manual intervention.

  Q: What is the difference between "Freeze" and "Ignore" modes in the v9.2 HA disarm
  workflow?

  A: "Freeze" mode halts any changes to the current operational state of your HA-managed
  guests, while the "Ignore" mode bypasses HA tracking of your HA-managed guests so
  that these appear as HA-unmanaged guests while the HA stack is disarmed. So you
  can work on nodes with any mode without triggering false-positive fence actions.

  Q: Does Proxmox VE 9.2 handle WireGuard crypto key distribution automatically?

  A: Yes. When using WireGuard as an SDN fabric protocol, public/private key distribution
  is fully automated across all joined cluster nodes.

  Q: What is the new stable kernel for Proxmox 9.2?

  A: Proxmox 9.2 defaults to Linux Kernel 7.0, providing the latest ZFS 2.4 features.

  Q: What software versions are bundled with the Proxmox 9.2 ISO?

  A: It is built on Debian 13.5 ("Trixie") running Linux Kernel 7.0, and includes
  QEMU 11.0, LXC 7.0, ZFS 2.4, and Ceph Tentacle 20.2.


  Learn more about Proxmox VE


  Forum announcement: https://forum.proxmox.com/

  Download: https://www.proxmox.com/downloads

  Enterprise support plans: https://www.proxmox.com

  Book a training: https://www.proxmox.com/training'
date: '2026-05-21'
year: 2026
week: 21
comments: []
---
