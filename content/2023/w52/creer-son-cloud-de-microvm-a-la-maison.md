---
title: Créer son cloud de MicroVM à la maison ?
url_link: https://une-tasse-de.cafe/blog/firecracker/
tags:
- cloud
- infrastructure
- networking
- devops
- automation
- containers
description: 'J''utilise constamment des machines virtuelles pour tester des scripts,
  pour héberger des services, pour faire des tests de déploiement, etc. J''ai pour
  habitude d''utiliser Proxmox dans le cadre de mon lab, et Libvirt au travail.

  Depuis peu, j''approfondis mes connaissances sur les clouds publiques comme AWS,
  GCP, Azure, etc. Et s''il y a bien une chose qui me fascine, c''est la vitesse à
  laquelle on peut créer une machine virtuelle.

  Il m''arrive d''utiliser Cloud-Init pour automatiser la création de mes machines
  virtuelles ou Packer pour créer des templates de VM, mais nous parlons de quelques
  minutes (et non de secondes).

  C''est en faisant mes recherches sur ce sujet que je suis tombé sur Firecracker,
  un projet open-source d''AWS qui permet de créer des microVMs en quelques millisecondes
  (oui oui, millisecondes). Alors, je veux pouvoir créer des machines virtuelles en
  quelques millisecondes, mais aussi pouvoir les détruire et les recréer à la volée.
  De ce fait, ces machines virtuelles pourront être utilisées pour des tests, pour
  des déploiements, pour des services, etc.'
date: '2023-12-29'
year: 2023
week: 52
comments: []
---


