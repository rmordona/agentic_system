git config --global http.postBuffer 524288000
git add --all
git commit -m "(POC) Re-factoring to decouple domain specific schema, tools, pipelines, and templates from agents to be more domain agnostic"
git push -u origin main
