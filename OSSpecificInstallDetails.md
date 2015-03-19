

# Rocks 5 & Centos 5 #

Install EPEL yum repo:
```
wget http://download.fedoraproject.org/pub/epel/5/i386/epel-release-5-4.noarch.rpm
rpm -Uvh epel-release-5-4.noarch.rpm 
```

Make sure the CentOS yum repo is enabled. If you're using Centos it probably already is. In Rocks you can copy /etc/yum.repos.d/CentOS-Base.repo from another machine.

Install virtualenv & subversion:
```
yum install python-virtualenv
yum install subversion
yum install java-1.6.0-openjdk
yum install gcc
```

Add the Nordugrid stuff:

```
rpm --import http://download.nordugrid.org/RPM-GPG-KEY-nordugrid
```

Create /etc/yum.repos.d/arc.repo so it looks like this:

```
[nordugrid]
name=NorduGrid - $basearch - stable
baseurl=http://download.nordugrid.org/repos/redhat/el5/$basearch/stable
enabled=1
gpgcheck=1
gpgkey=http://download.nordugrid.org/RPM-GPG-KEY-nordugrid

[nordugrid-testing]
name=NorduGrid - $basearch - testing
baseurl=http://download.nordugrid.org/repos/redhat/el5/$basearch/testing
enabled=0
gpgcheck=1
gpgkey=http://download.nordugrid.org/RPM-GPG-KEY-nordugrid

[nordugrid-experimental]
name=NorduGrid - $basearch - experimental
baseurl=http://download.nordugrid.org/repos/redhat/el5/$basearch/experimental
enabled=0
gpgcheck=1
gpgkey=http://download.nordugrid.org/RPM-GPG-KEY-nordugrid
```

Install nordugrid python components (Also install SMSCG voms stuff if that's how you roll):
```
yum install nordugrid-arc-python voms-clients ca_policy_*
wget http://repo.smscg.ch/SMSCG_WGET_CONFIG/smscg_ui_vomses
mv smscg_ui_vomses /etc/vomses
```

**Now follow the instructions from the _All Distributions_ section, below.**


# CentOS 4 #

Add your content here.  Format your content with:
  * Text in **bold** or _italic_
  * Headings, paragraphs, and lists
  * Automatic links to other wiki pages

**Now follow the instructions from the _All Distributions_ section, below.**


# CentOS 5 #

todo

**Now follow the instructions from the _All Distributions_ section, below.**


# Debian 5 #

```
aptitude install python-crypto 
aptitude install python-paramiko
```


Python-stats seems to conflict with pycli, either remove it or keep it out of your PYTHONPATH.

**Now follow the instructions from the _All Distributions_ section, below.**


# Debian 6 #

todo

**Now follow the instructions from the _All Distributions_ section, below.**


# All Distributions #


Install SLCS client:

```
mkdir ~/slcs
wget https://slcs.switch.ch/download/glite-slcs-ui-jdk1.5.tar.gz
tar xvfz glite-slcs-ui-jdk1.5.tar.gz -C ~/slcs
export PATH=$PATH:~/slcs/bin
export PYTHONPATH=$PYTHONPATH:/opt/nordugrid/lib64/python2.4/site-packages:/opt/nordugrid/lib/python2.4/site-packages
```

Setup your virtualenv:
```
virtualenv ~/gc3pie
. ~/gc3pie/bin/activate
```



Check out & install the source:

```
cd ~/gc3pie
svn co http://gc3pie.googlecode.com/svn/branches/1.0/gc3pie src
cd ~/gc3pie/src
./setup.py develop
```