include:
  - ..packages.python-pip
  
pip:
  pip.installed:
    - name: pip==9.0.3
    - upgrade: True
    - require:
      - pkg: python-pip
