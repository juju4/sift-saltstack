include:
  - ..packages.python-software-properties
  - ..packages.apt-transport-https

sift-docker-repo:
  pkgrepo.managed:
    - humanname: Docker
    - name: deb https://apt.dockerproject.org/repo ubuntu-{{ grains['lsb_distrib_codename'] }} main
    - dist: ubuntu-{{ grains['lsb_distrib_codename'] }}
    - file: /etc/apt/sources.list.d/docker.list
    - keyid: 58118E89F3A912897C070ADBF76221572C52609D
    - keyserver: hkp://p80.pool.sks-keyservers.net:80
    - refresh_db: true
    - require:
      - pkg: python-software-properties
      - pkg: apt-transport-https
