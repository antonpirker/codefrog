# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
    # basic config
    config.vm.hostname = "codefrog-dev"
    config.vm.box = "generic/ubuntu1804"

    # forwarded ports
    config.vm.network :forwarded_port, guest: 8000, host: 8000
    config.vm.network :forwarded_port, guest: 3000, host: 3000
    config.vm.network :forwarded_port, guest: 5432, host: 5432

    # synched folders
    config.vm.synced_folder ".", "/codefrog", type: "virtualbox"

    # provisioning
    config.vm.provision :shell, path: "scripts/vagrant/provision.sh"
    config.vm.provision :shell, path: "scripts/vagrant/provision_user.sh", privileged: false
    config.vm.provision :shell, path: "scripts/vagrant/startup.sh", run: "always"
end
