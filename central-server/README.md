## OS Install

### Ignition file

https://docs.fedoraproject.org/en-US/fedora-coreos/producing-ign/

https://docs.fedoraproject.org/en-US/fedora-coreos/authentication/

https://github.com/coreos/butane/releases

To change regenerate ignition file for the yaml config
```shell
butane --pretty --strict ignite.bu > ignite.ign
```
To serve ignition file
```shell
python3 -m http.server
```

### Base Instalation

https://docs.fedoraproject.org/en-US/fedora-coreos/bare-metal/

### Git + Docker 

Install docker-compose + git
```shell
sudo rpm-ostree install git docker-compose
```
get repo subfolder with all compose files
```shell
mkdir git && cd git
git init
git remote add -f origin https://github.com/etancik/home-automation.git
git sparse-checkout init
git sparse-checkout add "central-server/docker-compose/"
git sparse-checkout add "central-server/initial-config/"
git pull origin master
cd ..
```

### Initial config for modules
```shell
cp -r git/central-server/initial-config/* ~
```

### Modules
Run [Home Assitant](https://www.home-assistant.io/) 
```shell
docker-compose -f git/central-server/initial-config/homeassistant.yaml up -d
```
