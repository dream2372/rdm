#!/usr/bin/bash -e


TARGET_DIR=/data/openpilot
cd $TARGET_DIR

mv panda/ panda_tmp/
mv opendbc/ opendbc_tmp/
mv laika_repo/ laika_repo_tmp/
mv cereal/ cereal_tmp/
mv rednose_repo/ rednose_repo_tmp/
mv panda_bodyharness/ panda_bodyharness_tmp/

git submodule deinit --all -f
git submodule rm panda opendbc laika_repo rednose_repo panda_bodyharness
rm .gitmodules

mv panda_tmp/ panda/
mv opendbc_tmp/ opendbc/
mv laika_repo_tmp/ laika_repo/
mv cereal_tmp/  cereal/
mv rednose_rep_tmp/ rednose_repo/
mv panda_bodyharness_tmp/ panda_bodyharness/

git rm --cached panda
git rm --cached opendbc
git rm --cached laika_repo
git rm --cached cereal
git rm --cached rednose_repo
git rm --cached panda_bodyharness

rm panda/.git
rm opendbc/.git
rm laika_repo/.git
rm cereal/.git
rm rednose_repo/.git
rm panda_bodyharness/.git

git add panda
git add opendbc
git add laika_repo
git add cereal
git add rednose_repo
git add panda_bodyharness

git commit -m "flatten submodules"
