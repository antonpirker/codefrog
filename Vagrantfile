# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
    # basic config
    config.vm.hostname = "maintainer-dev-server"
    config.vm.box = "generic/ubuntu1804"

    # forwarded ports
    config.vm.network :forwarded_port, guest: 8000, host: 8000

    # synched folders
    config.vm.synced_folder ".", "/vagrant", type: "virtualbox"

    # provisioning
    config.vm.provision :shell, path: "scripts/vagrant/provision.sh"
    config.vm.provision :shell, path: "scripts/vagrant/provision_user.sh", privileged: false
    config.vm.provision :shell, path: "scripts/vagrant/startup.sh", run: "always"
end
