#!/usr/bin/env python3

from functools import cmp_to_key
import sys
import requests 
import json
import semver       # https://github.com/python-semver/python-semver/blob/master/src/semver/version.py

def semverMatches(this: semver.VersionInfo, other: str) -> bool:
    # https://github.com/npm/node-semver
    if other.startswith('~'):   
        # Tilde Ranges: 
        # Allows patch-level changes if a minor version is specified on the comparator. Allows minor-level changes if not.
        otherVersion = semver.VersionInfo.parse(other.strip('~'))
        return this.match('>=' + other.strip('~')) and this.match(f'<{ otherVersion.major }.{ (otherVersion.minor+1) }.0')

    if other.startswith('^'):   
        # Caret Ranges: 
        # Allows changes that do not modify the left-most non-zero element in the [major, minor, patch] tuple
        otherVersion = semver.VersionInfo.parse(other.strip('^'))

        if (this.major > 0):
            return this.match('>=' + other.strip('^')) and this.match(f'<{ (otherVersion.major + 1) }.0.0')
        if (this.minor > 0):
            return this.match('>=' + other.strip('^')) and this.match(f'<{ otherVersion.major }.{ otherVersion.minor + 1 }.0')

        return this.match('>=' + other.strip('^')) and this.match(f'<{ otherVersion.major }.{ otherVersion.minor }.{ (otherVersion.patch + 1)}')
    
    return this.match('==' + other)

baseurl = 'https://deps.dev/_/s/npm/p/'

def getPackageUrlName(packageName: str) -> str:
    urlPackageName = packageName.replace('@', '%40').replace('/', '%2F')
    return urlPackageName

def depsDevHasPackage(packageName: str) -> bool:
    packageResponse = requests.get(baseurl + getPackageUrlName(packageName) + '/v/')
    return packageResponse.ok

def depsDevGetPackageVersions(packageName: str):
    packageVersionsResponse = requests.get(baseurl + getPackageUrlName(packageName) + '/versions')
    if (not packageVersionsResponse.ok):
        return None

    packageVersions = packageVersionsResponse.json()

    # https://izziswift.com/how-to-sort-objects-by-multiple-keys-in-python/
    def comparer(left, right):
        return semver.compare(left['version'], right['version'])

    result = sorted(packageVersions['versions'], key=cmp_to_key(comparer))
    return result

def depsDevGetPackageVersion(packageName: str, versionNumber: str):
    packageVersionResponse = requests.get(baseurl + getPackageUrlName(packageName) + '/v/' + versionNumber)
    if (not packageVersionResponse.ok):
        return None

    packageVersion = packageVersionResponse.json()
    return packageVersion

def depsDevGetPackageVersionDependencies(packageName: str, versionNumber: str):
    packageVersionDependenciesResponse = requests.get(baseurl + getPackageUrlName(packageName) + '/v/' + versionNumber + '/dependencies')
    if (not packageVersionDependenciesResponse.ok):
        return None

    packageVersionDependencies = packageVersionDependenciesResponse.json()
    return packageVersionDependencies

def main():
    # https://realpython.com/python-command-line-arguments/
    opts = [opt for opt in sys.argv[1:] if opt.startswith("-")]
    args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]

    if '-?' in opts:
        print(f"""usage: { sys.argv[0] }
        -d ... "dependencies" (default)
        -dd ... "devDependencies"
        -all ... "dependencies" and "devDependencies"
    """)
        exit

    packageJsonFilename = 'package.json'

    if args:
        packageJsonFilename = args[0]

    packageJsonText = ''
    try:
        f = open(packageJsonFilename, mode='r', encoding='UTF-8')
        packageJsonText = f.read()
        f.close()
    except:
        print(f'Cannot open file { packageJsonFilename }')
        exit

    packageJson = json.loads(packageJsonText)

    sectionKeys = []
    if '-d' in opts:
        sectionKeys = ["dependencies"]
    if '-dd' in opts:
        sectionKeys = ["devDependencies"]
    if '-all' in opts:
        sectionKeys = ["dependencies", "devDependencies"]

    if not sectionKeys:
        sectionKeys = ["dependencies"]

    for sectionKey in sectionKeys:
        section = packageJson[sectionKey]
        if not section:
            print(f'Property { sectionKey } not found in { packageJsonFilename }')
            continue

        for packageName in section:
            print(packageName + ': ' + section[packageName])

            if not depsDevHasPackage(packageName):
                print('.. package not found')
                continue

            packageVersions = depsDevGetPackageVersions(packageName)    # sorted by ascending semver!
            if not packageVersions:
                print('.. no package versions received')
                continue

            requiredVersion = section[packageName]
            versionNumber = None

            for packageVersion in packageVersions:
                version = semver.VersionInfo.parse(packageVersion['version'])
                if semverMatches(version, requiredVersion):
                    # lowest matching version found
                    print(f'.. matching { section[packageName] } as { packageVersion["version"] }')
                    versionNumber = packageVersion['version']
                    break

            if not versionNumber:
                print('.. no matching version found')
                break

            packageVersion = depsDevGetPackageVersion(packageName, versionNumber)
            if not packageVersion:
                print('.. matching version not received')
                break

            packageVersionVersion = packageVersion['version']
            if 'deprecated' in packageVersionVersion and packageVersionVersion['deprecated']:
                print('.. ' + packageVersion['version']['deprecated'])

            if 'advisories' in packageVersionVersion and packageVersionVersion['advisories']:
                print('.. package ' + packageName + ' version ' + versionNumber + ' has advisories:')
                for adv in packageVersionVersion['advisories']:
                    print('.... ' + adv['severity'] + ' - ' + adv['title'])

            packageVersionDependencies = depsDevGetPackageVersionDependencies(packageName, versionNumber)
            if not packageVersionDependencies:
                print('.. no package version dependencies received')
                break

            for dep in packageVersionDependencies['dependencies']:
                if 'advisories' in dep and dep['advisories']:
                    print('.. package ' + packageName + ' version ' + versionNumber + ' dependencies have advisories:')
                    for adv in dep['advisories']:
                        print('.... ' + dep['package']['name'] + ' v ' + dep['version'] + ': ' + adv['severity'] + ' - ' + adv['title'])

main()
