include:
  - sift.packages.software-properties-common

openjdk-repo:
  pkgrepo.managed:
    - ppa: openjdk-r/ppa
    - keyid: DA1A4A13543B466853BAF164EB9B1D8886F44E2A
    - keyserver: hkp://p80.pool.sks-keyservers.net:80
    - refresh: true
    - require:
      - sls: sift.packages.software-properties-common
