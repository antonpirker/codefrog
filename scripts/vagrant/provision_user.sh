#!/usr/bin/env bash

echo "Setup shell..."

BASH_PROFILE="${HOME}/.bash_profile"
touch ${BASH_PROFILE}

cp /codefrog/scripts/.bash_prompt.sh ${HOME}
LINES=(
    "export PATH=\"/home/vagrant/.pyenv/bin:\$PATH\""
    "eval \"\$(pyenv init -)\""
    "eval \"\$(pyenv virtualenv-init -)\""

    "source ~/.bash_prompt.sh"
    "cd /codefrog"
)
for i in ${!LINES[@]}; do
    grep -q -F "${LINES[$i]}" "${BASH_PROFILE}" || echo "${LINES[$i]}" >> "${BASH_PROFILE}"
done
source ${BASH_PROFILE}


echo "Install pyenv..."

curl -s -S -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash || true
source ${BASH_PROFILE}


echo "Install python..."

cd /codefrog
pyenv install || true


echo "Install project requirements "

pip install --upgrade pip
pip install --disable-pip-version-check -r /codefrog/requirements.txt


echo "Running migrations "

cd /codefrog/codefrog
./manage.py migrate
