#!/usr/bin/env bash
# Create a new GH repository for a given project
# Usage: bash create-github-project.sh my-project-name

ORGANISATION="climate-resource"
REPO_NAME=$1

CR_ORG_ID=$(gh api graphql -F owner=$ORGANISATION -f query='
    query($owner: String!) {
      organization(login: $owner) {
        id
      }
    }
  ' | jq -r '.data.organization.id'
)


RESP=$(gh api graphql -F ownerId=$CR_ORG_ID -F name=$REPO_NAME -f query='
    mutation ($ownerId: ID!, $name: String!) {
      createRepository(
        input: {
          ownerId: $ownerId,
          name: $name,
          visibility: PUBLIC
        }
      )
      {
        repository {
          id,
          databaseId,
          name,
          url,
          sshUrl
        }
      }
  }
'
)
echo $RESP

REPO_ID=$(echo $RESP | jq -r '.data.createRepository.repository.databaseId')

# Set visibility to the access token
# This only works for public repos
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  /orgs/$ORGANISATION/actions/secrets/PERSONAL_ACCESS_TOKEN/repositories/$REPO_ID
