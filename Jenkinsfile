// Work in progress

node {

    try{
        currentBuild.result = "SUCCESS"
        def workspace = pwd()

        stage 'Clean Workspace'
            deleteDir()

        stage("Download source and capture commit ID") {
                checkout scm
                // Get the commit ID
                sh 'git rev-parse --verify HEAD > GIT_COMMIT'
                git_commit = readFile('GIT_COMMIT').take(7)
                echo "Current commit ID: ${git_commit}"
        }

        stage("Build and verify 1"){
                defaultplatform = sh (
                    script: '''#!/bin/bash
kitchen list | awk "!/Instance/ {print \\$1; exit}"
                        ''',
                    returnStdout: true
                    ).trim()
                echo "default platform: ${defaultplatform}"

                sh "kitchen test ${defaultplatform}"
                // must keep instance for security testing after
                //sh "kitchen verify ${defaultplatform}"
        }

        stage("Cleanup if no errors"){
                sh "kitchen destroy"
        }

    }

    catch(err) {
        currentBuild.result = "FAILURE"
        throw err
    }
}
