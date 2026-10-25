---
title: 'OpenAI Turned BGP Off: An SRv6 Fabric With No Routing Protocol, ~50 ms Failover'
url_link: https://www.youtube.com/watch?v=ef1tnHXA1JU
tags:
- networking
- infrastructure
description: 'OpenAI''s MRC fabric runs no routing protocol. No BGP, no OSPF, no IS-IS
  between the switches. So how do packets find their way, and what happens when a
  link dies? A team of AI agents built a small copy of the idea in GNS3 on FRRouting
  10.5: 2 spines, 3 leaves, SRv6 micro-SIDs (uSID), static config only. Then we cut
  a link live.


  The live result: with nothing but a 45-line bash path agent on each host, plane
  2 was declared down after 3 missed probes. The ping went from icmp_seq 4437 to 4443:
  5 packets lost at 100 per second, about 50 ms. Episode 2''s eBGP fabric took 6 to
  9 seconds. With the agent turned off, the flow pinned to the dead plane stays lost
  until the link comes back, because a static fabric does not heal itself.


  The honest part: static routes ARE routing. The routing didn''t disappear, it moved
  out of the switches and into the host. And our bash agent is milliseconds, not the
  microseconds that MRC gets in the NIC hardware.


  Free lab kit: the SRv6 fabric and the path agent in containerlab, one command, plus
  the lesson, both animations and the exercises:

  https://www.grahampaasch.com/labs/srv...


  What you''ll learn:

  The ticket punch: one IPv6 address (fcbb:bb00:100:3:fe00::) carries the whole path,
  and each switch "punches" its own 16-bit uSID and shifts the rest left

  The entire switch config: zebra + staticd, a locator, one End.DX4 unwrap rule. Nothing
  listening on TCP 179

  What the host does: two seg6 encap next hops, packet spraying across planes, probes
  at 100 per second per path

  Live: 1000 flows sprayed about half and half across two planes, nobody negotiated

  Live: fail link 2 with the agent off (never heals) and on (~50 ms)

  Wireshark: the path is in the packet (the SRv6 header, the segment list, the IPv4
  packet inside)

  What we can''t reproduce, and the tuning-knob trade-off

  Exercises: add a third stop, who notices a dead link, drop the 24-byte header


  Episode 1 (AI-cluster fabric with BGP unnumbered, ECMP and BFD):    • AI Agents Built My Network Lab Live: BGP U...  

  Episode 2 (BGP vs OSPF, blast radius):    • BGP Is an App, Not an IGP: OSPF vs eBGP Tw...  

  The whole series, "AI Agents Build the Lab":    • AI Agents Build the Lab  

  How my voice agent, Cadence, works: https://www.grahampaasch.com/cadence


  Chapters:

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=0s" target="_blank" rel="noopener">00:00</a>
  - Cold open: OpenAI turned BGP off

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=63s" target="_blank" rel="noopener">01:03</a>
  - Why this episode (an AI picked the topic)

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=209s" target="_blank" rel="noopener">03:29</a>
  - The agents build it (timelapse)

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=268s" target="_blank" rel="noopener">04:28</a>
  - The idea: the switches don''t route, the host does

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=553s" target="_blank" rel="noopener">09:13</a>
  - The ticket punch: one address, three stops

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=837s" target="_blank" rel="noopener">13:57</a>
  - Topology and SID plan

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=942s" target="_blank" rel="noopener">15:42</a>
  - The entire switch config

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=1167s" target="_blank" rel="noopener">19:27</a>
  - Animation: The Ticket Punch

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=1303s" target="_blank" rel="noopener">21:43</a>
  - What the host does (the path agent)

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=1447s" target="_blank" rel="noopener">24:07</a>
  - Demo: no routing protocol, traffic still flows

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=1705s" target="_blank" rel="noopener">28:25</a>
  - Spray: 1000 flows, nobody negotiated

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=1849s" target="_blank" rel="noopener">30:49</a>
  - Fail link 2 with the agent OFF

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=1956s" target="_blank" rel="noopener">32:36</a>
  - Fail link 2 with the agent ON (~50 ms)

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=2160s" target="_blank" rel="noopener">36:00</a>
  - Wireshark: the path is in the packet

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=2247s" target="_blank" rel="noopener">37:27</a>
  - Animation: The Path Is in the Packet

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=2337s" target="_blank" rel="noopener">38:57</a>
  - What we can''t reproduce (and static routes ARE routing)

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=2509s" target="_blank" rel="noopener">41:49</a>
  - The numbers: 6-9 s vs ~50-70 ms

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=2704s" target="_blank" rel="noopener">45:04</a>
  - Exercises: a third stop, a dead link, drop the header

  <a href="https://www.youtube.com/watch?v=ef1tnHXA1JU&t=2911s" target="_blank" rel="noopener">48:31</a>
  - Sources + Mark Handley''s animation


  Sources:

  OpenAI, Supercomputer networking to accelerate large-scale AI training (MRC), with
  Mark Handley''s packet-spraying animation: https://openai.com/index/mrc-supercom...

  arXiv 2605.04333, Resilient AI Supercomputer Networking using MRC and SRv6: https://arxiv.org/abs/2605.04333

  IETF draft-filsfils-srv6ops-srv6-ai-backend, SRv6 for AI backend networks: https://datatracker.ietf.org/doc/draf...

  Cisco, MRC and SRv6: https://blogs.cisco.com/datacenter/mr...

  Linux ip-route (seg6 encap): https://man7.org/linux/man-pages/man8...

  FRRouting: https://frrouting.org/  GNS3: https://www.gns3.com/  containerlab: https://containerlab.dev/

  Agent Standup by Atoll92 (MIT), the agent "video call": https://github.com/Atoll92/agent-standup


  Animations "The Ticket Punch" and "The Path Is in the Packet" were made by Cadence
  during the recording, from the real bytes of tonight''s captures.

  Lab: GNS3 + FRRouting 10.5.5, 2 spines, 3 leaves, 3 hosts. Agents: Claude Code sub-agents
  on the Agent Standup call, run by my voice assistant, Cadence.'
date: '2026-10-25'
year: 2026
week: 43
comments: []
---
