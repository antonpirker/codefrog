#!/usr/bin/env bash

echo "Setup shell..."

BASH_PROFILE="${HOME}/.bash_profile"
touch ${BASH_PROFILE}

cp /maintainer/scripts/.bash_prompt.sh ${HOME}
LINES=(
    "export PATH=\"/home/vagrant/.pyenv/bin:\$PATH\""
    "eval \"\$(pyenv init -)\""
    "eval \"\$(pyenv virtualenv-init -)\""

    "source ~/.bash_prompt.sh"
    "cd /maintainer"
)
for i in ${!LINES[@]}; do
    grep -q -F "${LINES[$i]}" "${BASH_PROFILE}" || echo "${LINES[$i]}" >> "${BASH_PROFILE}"
done
source ${BASH_PROFILE}


echo "Install pyenv..."

curl -s -S -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
source ${BASH_PROFILE}


echo "Install python..."

cd /maintainer
pyenv install


echo "Install project requirements "

pip install --upgrade pip
pip install --disable-pip-version-check -r /maintainer/requirements/dev.txt


echo "Running migrations "

cd /maintainer/maintainer
./manage.py migrate