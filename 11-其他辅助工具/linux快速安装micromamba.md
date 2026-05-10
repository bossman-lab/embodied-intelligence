sudo apt install bzip2



curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
#./bin/micromamba shell init -s bash -p /opt/micromamba
最新版本不支持-p命令了

./bin/micromamba shell init -s bash --root-prefix ./micromamba

vi ~/.bashrc
加上
alias mamba=micromamba


然后配置.condarc
