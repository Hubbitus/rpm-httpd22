%define contentdir /var/www/httpd22
%define suexec_caller apache
%define mmn 20051115
%define mmnisa %{mmn}%{__isa_name}-%{__isa_bits}
%define vstring Fedora
%define mpms worker event
%define all_services httpd22.service httpd22-worker.service httpd22-event.service

Summary: Apache HTTP Server
Name: httpd22
Version: 2.2.23
Release: 3%{?dist}
URL: http://httpd.apache.org/
Source0: http://www.apache.org/dist/httpd/httpd-%{version}.tar.bz2
Source1: index.html
Source3: httpd22.logrotate
Source5: httpd22.sysconf
Source6: httpd22-ssl-pass-dialog
Source10: httpd.conf
Source11: ssl.conf
Source12: welcome.conf
Source13: manual.conf
Source14: httpd22.tmpfiles
Source15: httpd22.service
# Documentation
Source31: httpd22.mpm.xml
Source33: README.confd
# build/scripts patches
Patch1: httpd-2.1.10-apctl.patch
Patch2: httpd-2.1.10-apxs.patch
Patch3: httpd-2.2.9-deplibs.patch
Patch4: httpd-2.1.10-disablemods.patch
Patch5: httpd-2.2.22-layout.patch
# Features/functional changes
Patch20: httpd-2.0.48-release.patch
Patch22: httpd-2.1.10-pod.patch
Patch23: httpd-2.0.45-export.patch
Patch24: httpd-2.2.11-corelimit.patch
Patch25: httpd-2.2.11-selinux.patch
Patch26: httpd-2.2.9-suenable.patch
Patch27: httpd-2.2.19-logresolve-ipv6.patch
Patch28: httpd-2.2.21-mod_proxy-change-state.patch
License: ASL 2.0
Group: System Environment/Daemons
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
BuildRequires: autoconf, perl, pkgconfig, findutils, xmlto
BuildRequires: zlib-devel, libselinux-devel
BuildRequires: apr-devel >= 1.2.0, apr-util-devel >= 1.2.0, pcre-devel >= 5.0
Requires: /etc/mime.types, system-logos >= 7.92.1-1
Obsoletes: httpd-suexec
Provides: webserver
Provides: mod_dav = %{version}-%{release}, httpd-suexec = %{version}-%{release}
Provides: httpd-mmn = %{mmn}, httpd-mmn = %{mmnisa}
Requires: httpd22-tools = %{version}-%{release}, apr-util-ldap
Requires(pre): /usr/sbin/useradd
Requires(preun): systemd-units
Requires(postun): systemd-units
Requires(post): systemd-units

%description
The Apache HTTP Server is a powerful, efficient, and extensible
web server.

%package devel
Group: Development/Libraries
Summary: Development interfaces for the Apache HTTP server
Obsoletes: secureweb-devel, apache-devel, stronghold-apache-devel
Requires: apr-devel, apr-util-devel, pkgconfig
Requires: httpd22 = %{version}-%{release}

%description devel
The httpd22-devel package contains the APXS binary and other files
that you need to build Dynamic Shared Objects (DSOs) for the
Apache HTTP Server.

If you are installing the Apache HTTP server and you want to be
able to compile or develop additional modules for Apache, you need
to install this package.

%package manual
Group: Documentation
Summary: Documentation for the Apache HTTP server
Requires: httpd22 = %{version}-%{release}
Obsoletes: secureweb-manual, apache-manual
BuildArch: noarch

%description manual
The httpd22-manual package contains the complete manual and
reference guide for the Apache HTTP server. The information can
also be found at http://httpd.apache.org/docs/2.2/.

%package tools
Group: System Environment/Daemons
Summary: Tools for use with the Apache HTTP Server

%description tools
The httpd22-tools package contains tools which can be used with
the Apache HTTP Server.

%package -n mod_ssl
Group: System Environment/Daemons
Summary: SSL/TLS module for the Apache HTTP Server
Epoch: 1
BuildRequires: openssl-devel
Requires(post): openssl, /bin/cat
Requires(pre): httpd22
Requires: httpd = 0:%{version}-%{release}, httpd-mmn = %{mmnisa}
Obsoletes: stronghold-mod_ssl

%description -n mod_ssl
The mod_ssl module provides strong cryptography for the Apache Web
server via the Secure Sockets Layer (SSL) and Transport Layer
Security (TLS) protocols.

%prep
%setup -q -n httpd-%{version}
%patch1 -p1 -b .apctl
%patch2 -p1 -b .apxs
%patch3 -p1 -b .deplibs
%patch4 -p1 -b .disablemods
%patch5 -p1 -b .layout

%patch22 -p1 -b .pod
%patch23 -p1 -b .export
%patch24 -p1 -b .corelimit
%patch25 -p1 -b .selinux
%patch26 -p1 -b .suenable
%patch27 -p1 -b .logresolve-ipv6
%patch28 -p1 -b .mod_proxy-change-state

# Patch in vendor/release string
sed "s/@RELEASE@/%{vstring}/" < %{PATCH20} | patch -p1

# Safety check: prevent build if defined MMN does not equal upstream MMN.
vmmn=`echo MODULE_MAGIC_NUMBER_MAJOR | cpp -include include/ap_mmn.h | sed -n '/^2/p'`
if test "x${vmmn}" != "x%{mmn}"; then
   : Error: Upstream MMN is now ${vmmn}, packaged MMN is %{mmn}
   : Update the mmn macro and rebuild.
   exit 1
fi

: Building with MMN %{mmn}, MMN-ISA %{mmnisa} and vendor string '%{vstring}'

%build
# forcibly prevent use of bundled apr, apr-util, pcre
rm -rf srclib/{apr,apr-util,pcre}

# regenerate configure scripts
autoheader && autoconf || exit 1

# Before configure; fix location of build dir in generated apxs
%{__perl} -pi -e "s:\@exp_installbuilddir\@:%{_libdir}/httpd22/build:g" \
	support/apxs.in

export CFLAGS=$RPM_OPT_FLAGS
export LDFLAGS="-Wl,-z,relro,-z,now"

# Hard-code path to links to avoid unnecessary builddep
export LYNX_PATH=/usr/bin/links

function mpmbuild()
{
mpm=$1; shift

# Build the systemd file
sed "s,@NAME@,${mpm},g;s,@EXEC@,%{_sbindir}/httpd22.${mpm},g" %{SOURCE15} > httpd22-${mpm}.service
touch -r %{SOURCE15} httpd22-${mpm}.service

# Build the man page
ymdate=`date +'%b %Y'`
sed "s/@PROGNAME@/httpd.${mpm}/g;s/@DATE@/${ymdate}/g;s/@VERSION@/%{version}/g;s/@MPM@/${mpm}/g;" \
    < $RPM_SOURCE_DIR/httpd22.mpm.xml > httpd22.${mpm}.8.xml
xmlto man httpd22.${mpm}.8.xml && mv httpd.${mpm}.8 httpd22.${mpm}.8

# Build the daemon
mkdir $mpm; pushd $mpm
../configure \
	--prefix=%{_sysconfdir}/httpd22 \
	--exec-prefix=%{_prefix} \
	--bindir=%{_bindir} \
	--sbindir=%{_sbindir} \
	--mandir=%{_mandir} \
	--libdir=%{_libdir} \
	--sysconfdir=%{_sysconfdir}/httpd22/conf \
	--includedir=%{_includedir}/httpd22 \
	--libexecdir=%{_libdir}/httpd22/modules \
	--datadir=%{contentdir} \
	--with-installbuilddir=%{_libdir}/httpd22/build \
	--with-mpm=$mpm \
	--with-apr=%{_prefix} --with-apr-util=%{_prefix} \
	--enable-suexec --with-suexec \
	--with-suexec-caller=%{suexec_caller} \
	--with-suexec-docroot=%{contentdir} \
	--with-suexec-logfile=%{_localstatedir}/log/httpd22/suexec.log \
	--with-suexec-bin=%{_sbindir}/suexec \
	--with-suexec-uidmin=500 --with-suexec-gidmin=100 \
	--enable-pie \
	--with-pcre \
	$*

make %{?_smp_mflags}

mv httpd httpd22

popd
}

# Build everything and the kitchen sink with the prefork build
mpmbuild prefork \
	--enable-mods-shared=all \
	--enable-ssl --with-ssl --disable-distcache \
	--enable-proxy \
	--enable-cache \
	--enable-disk-cache \
	--enable-ldap --enable-authnz-ldap \
	--enable-cgid \
	--enable-authn-anon --enable-authn-alias \
	--disable-imagemap

# For the other MPMs, just build httpd22 and no optional modules
for f in %{mpms}; do
   mpmbuild $f --enable-modules=none
done

# Create default/prefork service file for systemd
sed "s,@NAME@,prefork,g;s,@EXEC@,%{_sbindir}/httpd22,g" %{SOURCE15} > httpd22.service
touch -r %{SOURCE15} httpd22.service

%install
rm -rf $RPM_BUILD_ROOT

pushd prefork
make DESTDIR=$RPM_BUILD_ROOT install
popd

# install alternative MPMs; executables, man pages, and systemd service files
mkdir -p $RPM_BUILD_ROOT/lib/systemd/system
for f in %{mpms}; do
  install -m 755 ${f}/httpd22 $RPM_BUILD_ROOT%{_sbindir}/httpd22.${f}
  install -m 644 httpd22.${f}.8 $RPM_BUILD_ROOT%{_mandir}/man8/httpd22.${f}.8
  install -p -m 644 httpd22-${f}.service \
          $RPM_BUILD_ROOT/lib/systemd/system/httpd22-${f}.service
done
mv $RPM_BUILD_ROOT%{_sbindir}/httpd $RPM_BUILD_ROOT%{_sbindir}/httpd22

# Default httpd22 (prefork) service file
install -p -m 644 httpd22.service \
        $RPM_BUILD_ROOT/lib/systemd/system/httpd22.service

# install conf file/directory
mkdir $RPM_BUILD_ROOT%{_sysconfdir}/httpd22/conf.d
install -m 644 $RPM_SOURCE_DIR/README.confd \
    $RPM_BUILD_ROOT%{_sysconfdir}/httpd22/conf.d/README
for f in ssl.conf welcome.conf manual.conf; do
  install -m 644 -p $RPM_SOURCE_DIR/$f \
        $RPM_BUILD_ROOT%{_sysconfdir}/httpd22/conf.d/$f
done

rm $RPM_BUILD_ROOT%{_sysconfdir}/httpd22/conf/*.conf
install -m 644 -p $RPM_SOURCE_DIR/httpd.conf \
   $RPM_BUILD_ROOT%{_sysconfdir}/httpd22/conf/httpd.conf

mkdir $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig
install -m 644 -p $RPM_SOURCE_DIR/httpd22.sysconf \
   $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/httpd22

# tmpfiles.d configuration
mkdir $RPM_BUILD_ROOT%{_sysconfdir}/tmpfiles.d
install -m 644 -p $RPM_SOURCE_DIR/httpd22.tmpfiles \
   $RPM_BUILD_ROOT%{_sysconfdir}/tmpfiles.d/httpd22.conf

# for holding mod_dav lock database
mkdir -p $RPM_BUILD_ROOT%{_localstatedir}/lib/dav

# create a prototype session cache
mkdir -p $RPM_BUILD_ROOT%{_localstatedir}/cache/mod_ssl
touch $RPM_BUILD_ROOT%{_localstatedir}/cache/mod_ssl/scache.{dir,pag,sem}

# create cache root
mkdir $RPM_BUILD_ROOT%{_localstatedir}/cache/mod_proxy

# move utilities to /usr/bin and rename mans
for i in ab htdbm logresolve htpasswd htdigest; do
   [ -f $RPM_BUILD_ROOT%{_sbindir}/$i ] && mv $RPM_BUILD_ROOT%{_sbindir}/$i $RPM_BUILD_ROOT%{_bindir}/${i}22
   [ -f $RPM_BUILD_ROOT%{_mandir}/man1/${i}.1 ] && mv $RPM_BUILD_ROOT%{_mandir}/man1/${i}.1 $RPM_BUILD_ROOT%{_mandir}/man1/${i}22.1
   [ -f $RPM_BUILD_ROOT%{_mandir}/man8/${i}.8 ] && mv $RPM_BUILD_ROOT%{_mandir}/man8/${i}.8 $RPM_BUILD_ROOT%{_mandir}/man8/${i}22.8
done

# Make the MMN accessible to module packages
echo %{mmnisa} > $RPM_BUILD_ROOT%{_includedir}/httpd22/.mmn
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/rpm
cat > $RPM_BUILD_ROOT%{_sysconfdir}/rpm/macros.httpd22 <<EOF
%%_httpd22_mmn %{mmnisa}
%%_httpd22_apxs %%{_sbindir}/apxs22
%%_httpd22_modconfdir %%{_sysconfdir}/httpd22/conf.d
%%_httpd22_confdir %%{_sysconfdir}/httpd22/conf.d
%%_httpd22_contentdir %{contentdir}
%%_httpd22_moddir %%{_libdir}/httpd22/modules
EOF

# docroot
mkdir $RPM_BUILD_ROOT%{contentdir}/html
install -m 644 -p $RPM_SOURCE_DIR/index.html \
        $RPM_BUILD_ROOT%{contentdir}/error/noindex.html

# remove manual sources
find $RPM_BUILD_ROOT%{contentdir}/manual \( \
    -name \*.xml -o -name \*.xml.* -o -name \*.ent -o -name \*.xsl -o -name \*.dtd \
    \) -print0 | xargs -0 rm -f

# Strip the manual down just to English and replace the typemaps with flat files:
set +x
for f in `find $RPM_BUILD_ROOT%{contentdir}/manual -name \*.html -type f`; do
   if test -f ${f}.en; then
      cp ${f}.en ${f}
      rm ${f}.*
   fi
done
set -x

# Symlink for the powered-by-$DISTRO image:
ln -s ../../..%{_datadir}/pixmaps/poweredby.png \
        $RPM_BUILD_ROOT%{contentdir}/icons/poweredby.png

# symlinks for /etc/httpd22
ln -s ../..%{_localstatedir}/log/httpd22 $RPM_BUILD_ROOT/etc/httpd22/logs
ln -s ../..%{_localstatedir}/run/httpd22 $RPM_BUILD_ROOT/etc/httpd22/run
ln -s ../..%{_libdir}/httpd22/modules $RPM_BUILD_ROOT/etc/httpd22/modules

# install http-ssl-pass-dialog
mkdir -p $RPM_BUILD_ROOT/%{_libexecdir}
install -m755 $RPM_SOURCE_DIR/httpd22-ssl-pass-dialog \
	$RPM_BUILD_ROOT/%{_libexecdir}/httpd22-ssl-pass-dialog

# install log rotation stuff
mkdir -p $RPM_BUILD_ROOT/etc/logrotate.d
install -m 644 -p $RPM_SOURCE_DIR/httpd22.logrotate \
	$RPM_BUILD_ROOT/etc/logrotate.d/httpd22

# fix man page paths
sed -e "s|/usr/local/apache2/conf/httpd22.conf|/etc/httpd22/conf/httpd.conf|" \
    -e "s|/usr/local/apache2/conf/mime.types|/etc/mime.types|" \
    -e "s|/usr/local/apache2/conf/magic|/etc/httpd22/conf/magic|" \
    -e "s|/usr/local/apache2/logs/error_log|/var/log/httpd22/error_log|" \
    -e "s|/usr/local/apache2/logs/access_log|/var/log/httpd22/access_log|" \
    -e "s|/usr/local/apache2/logs/httpd22.pid|/var/run/httpd22/httpd22.pid|" \
    -e "s|/usr/local/apache2|/etc/httpd22|" < docs/man/httpd.8 \
  > $RPM_BUILD_ROOT%{_mandir}/man8/httpd22.8

# Make ap_config_layout.h libdir-agnostic
sed -i '/.*DEFAULT_..._LIBEXECDIR/d;/DEFAULT_..._INSTALLBUILDDIR/d' \
    $RPM_BUILD_ROOT%{_includedir}/httpd22/ap_config_layout.h

# Fix path to instdso in special.mk
sed -i '/instdso/s,top_srcdir,top_builddir,' \
    $RPM_BUILD_ROOT%{_libdir}/httpd22/build/special.mk

# Remove unpackaged files
rm -f $RPM_BUILD_ROOT%{_libdir}/*.exp \
      $RPM_BUILD_ROOT/etc/httpd22/conf/mime.types \
      $RPM_BUILD_ROOT%{_libdir}/httpd22/modules/*.exp \
      $RPM_BUILD_ROOT%{_libdir}/httpd22/build/config.nice \
      $RPM_BUILD_ROOT%{_bindir}/ap?-config \
      $RPM_BUILD_ROOT%{_sbindir}/{checkgid,dbmmanage,envvars*} \
      $RPM_BUILD_ROOT%{contentdir}/htdocs/* \
      $RPM_BUILD_ROOT%{_mandir}/man1/dbmmanage.* \
      $RPM_BUILD_ROOT%{contentdir}/cgi-bin/*

rm -rf $RPM_BUILD_ROOT/etc/httpd22/conf/{original,extra}

#+Hu RENAME all with 22 suffix:
# Make suexec a+rw so it can be stripped.  %%files lists real permissions
mv $RPM_BUILD_ROOT%{_sbindir}/suexec $RPM_BUILD_ROOT%{_sbindir}/suexec22
chmod 755 $RPM_BUILD_ROOT%{_sbindir}/suexec22

# rename apxs.8 to apxs.1
mv $RPM_BUILD_ROOT%{_mandir}/man8/apxs.8 $RPM_BUILD_ROOT%{_mandir}/man1/apxs22.1

for i in htcacheclean httxt2dbm apxs apachectl rotatelogs; do
	mv $RPM_BUILD_ROOT%{_sbindir}/$i $RPM_BUILD_ROOT%{_sbindir}/${i}22;
	[ -f $RPM_BUILD_ROOT%{_mandir}/man8/$i.8 ] && mv $RPM_BUILD_ROOT%{_mandir}/man8/$i.8 $RPM_BUILD_ROOT%{_mandir}/man8/${i}22.8
done

mv $RPM_BUILD_ROOT%{_mandir}/man1/httxt2dbm.1 $RPM_BUILD_ROOT%{_mandir}/man1/httxt2dbm22.1
mv $RPM_BUILD_ROOT%{_mandir}/man8/suexec.8 $RPM_BUILD_ROOT%{_mandir}/man8/suexec22.8
# Leave only *22.8
rm $RPM_BUILD_ROOT%{_mandir}/man8/httpd.8

%pre
# Add the "apache" user
/usr/sbin/useradd -c "Apache" -u 48 \
	-s /sbin/nologin -r -d %{contentdir} apache 2> /dev/null || :

%post
# Register the httpd22 service
if [ $1 -eq 1 ] ; then
    # Initial installation
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
fi

%preun
if [ $1 -eq 0 ] ; then
    # Package removal, not upgrade
    /bin/systemctl --no-reload disable %{all_services} > /dev/null 2>&1 || :
    /bin/systemctl stop %{all_services} > /dev/null 2>&1 || :
fi

%postun
/bin/systemctl daemon-reload >/dev/null 2>&1 || :

# Trigger for conversion from SysV, per guidelines at:
# https://fedoraproject.org/wiki/Packaging:ScriptletSnippets#Systemd
%triggerun -- httpd22 < 2.2.21-5
# Save the current service runlevel info
# User must manually run systemd-sysv-convert --apply httpd22
# to migrate them to systemd targets
/usr/bin/systemd-sysv-convert --save httpd22.service >/dev/null 2>&1 ||:

# Run these because the SysV package being removed won't do them
/sbin/chkconfig --del httpd22 >/dev/null 2>&1 || :

%posttrans
/bin/systemctl try-restart %{all_services} >/dev/null 2>&1 || :

%define sslcert %{_sysconfdir}/pki/tls/certs/localhost.crt
%define sslkey %{_sysconfdir}/pki/tls/private/localhost.key

%post -n mod_ssl
umask 077

if [ -f %{sslkey} -o -f %{sslcert} ]; then
   exit 0
fi

%{_bindir}/openssl genrsa -rand /proc/apm:/proc/cpuinfo:/proc/dma:/proc/filesystems:/proc/interrupts:/proc/ioports:/proc/pci:/proc/rtc:/proc/uptime 1024 > %{sslkey} 2> /dev/null

FQDN=`hostname`
if [ "x${FQDN}" = "x" ]; then
   FQDN=localhost.localdomain
fi

cat << EOF | %{_bindir}/openssl req -new -key %{sslkey} \
         -x509 -days 365 -set_serial $RANDOM -extensions v3_req \
         -out %{sslcert} 2>/dev/null
--
SomeState
SomeCity
SomeOrganization
SomeOrganizationalUnit
${FQDN}
root@${FQDN}
EOF

%check
# Check the built modules are all PIC
if readelf -d $RPM_BUILD_ROOT%{_libdir}/httpd22/modules/*.so | grep TEXTREL; then
   : modules contain non-relocatable code
   exit 1
fi

# Verify that the same modules were built into the httpd22 binaries
./prefork/httpd22 -l | grep -v prefork > prefork.mods
for mpm in %{mpms}; do
  ./${mpm}/httpd22 -l | grep -v ${mpm} > ${mpm}.mods
  if ! diff -u prefork.mods ${mpm}.mods; then
    : Different modules built into httpd22 binaries, will not proceed
    exit 1
  fi
done

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)

%doc ABOUT_APACHE README CHANGES LICENSE VERSIONING NOTICE

%dir %{_sysconfdir}/httpd22
%{_sysconfdir}/httpd22/modules
%{_sysconfdir}/httpd22/logs
%{_sysconfdir}/httpd22/run
%dir %{_sysconfdir}/httpd22/conf
%config(noreplace) %{_sysconfdir}/httpd22/conf/httpd.conf
%config(noreplace) %{_sysconfdir}/httpd22/conf.d/welcome.conf
%config(noreplace) %{_sysconfdir}/httpd22/conf/magic

%config(noreplace) %{_sysconfdir}/logrotate.d/httpd22

%dir %{_sysconfdir}/httpd22/conf.d
%{_sysconfdir}/httpd22/conf.d/README

%config(noreplace) %{_sysconfdir}/sysconfig/httpd22
%config %{_sysconfdir}/tmpfiles.d/httpd22.conf

%{_sbindir}/httpd22
%{_mandir}/man8/httpd22.8.gz
%{_sbindir}/httpd22.event
%{_mandir}/man8/httpd22.event.8.gz
%{_sbindir}/httpd22.worker
%{_mandir}/man8/httpd22.worker.8.gz
%{_sbindir}/htcacheclean22
%{_mandir}/man8/htcacheclean22.8.gz
%{_sbindir}/httxt2dbm22
%{_mandir}/man1/httxt2dbm22.1.gz
%{_sbindir}/apachectl22
%{_mandir}/man8/apachectl22.8.gz
%{_sbindir}/rotatelogs22
%{_mandir}/man8/rotatelogs22.8.gz
# cap_dac_override needed to write to /var/log/httpd22
%caps(cap_setuid,cap_setgid,cap_dac_override+pe) %attr(510,root,%{suexec_caller}) %{_sbindir}/suexec22
%{_mandir}/man8/suexec22.8.gz

%dir %{_libdir}/httpd22
%dir %{_libdir}/httpd22/modules
%{_libdir}/httpd22/modules/mod*.so
%exclude %{_libdir}/httpd22/modules/mod_ssl.so

%dir %{contentdir}
%dir %{contentdir}/cgi-bin
%dir %{contentdir}/html
%dir %{contentdir}/icons
%dir %{contentdir}/error
%dir %{contentdir}/error/include
%{contentdir}/icons/*
%{contentdir}/error/README
%{contentdir}/error/noindex.html
%config %{contentdir}/error/*.var
%config %{contentdir}/error/include/*.html

%attr(0710,root,apache) %dir %{_localstatedir}/run/httpd22
%attr(0700,root,root) %dir %{_localstatedir}/log/httpd22
%attr(0700,apache,apache) %dir %{_localstatedir}/lib/dav
%attr(0700,apache,apache) %dir %{_localstatedir}/cache/mod_proxy

/lib/systemd/system/*.service

%files tools
%defattr(-,root,root)
%{_bindir}/ab22
%{_mandir}/man8/ab22.8.gz
%{_bindir}/htdbm22
%{_mandir}/man1/htdbm22.1.gz
%{_bindir}/htdigest22
%{_mandir}/man1/htdigest22.1.gz
%{_bindir}/htpasswd22
%{_mandir}/man1/htpasswd22.1.gz
%{_bindir}/logresolve22
%{_mandir}/man8/logresolve22.8.gz
%doc LICENSE NOTICE

%files manual
%defattr(-,root,root)
%{contentdir}/manual
%config %{_sysconfdir}/httpd22/conf.d/manual.conf

%files -n mod_ssl
%defattr(-,root,root)
%{_libdir}/httpd22/modules/mod_ssl.so
%config(noreplace) %{_sysconfdir}/httpd22/conf.d/ssl.conf
%attr(0700,apache,root) %dir %{_localstatedir}/cache/mod_ssl
%attr(0600,apache,root) %ghost %{_localstatedir}/cache/mod_ssl/scache.dir
%attr(0600,apache,root) %ghost %{_localstatedir}/cache/mod_ssl/scache.pag
%attr(0600,apache,root) %ghost %{_localstatedir}/cache/mod_ssl/scache.sem
%{_libexecdir}/httpd22-ssl-pass-dialog

%files devel
%defattr(-,root,root)
%{_includedir}/httpd22
%{_sbindir}/apxs22
%{_mandir}/man1/apxs22.1*
%dir %{_libdir}/httpd22/build
%{_libdir}/httpd22/build/*.mk
%{_libdir}/httpd22/build/*.sh
%{_sysconfdir}/rpm/macros.httpd22

%changelog
* Mon Mar 23 2015 Pavel Alexeev <Pahan@Hubbitus.info> - 2.2.23-3
- Adjust logrotate pathes.

* Mon Mar 16 2015 Pavel Alexeev <Pahan@Hubbitus.info> - 2.2.23-2
- Rename package into httpd22. Introduce for 1C web-services which does not work on Apache 2.4.
- Explicit list files, man, hack configs.

* Tue Jan 29 2013 Jan Kaluza <jkaluza@redhat.com> - 2.2.23-1
- update to 2.2.23

* Mon Apr 30 2012 Joe Orton <jorton@redhat.com> - 2.2.22-4
- switch default runtimedir to /var/run/httpd
- extend _httpd_* macro set per proposed guidelines
- fix comments in sysconfig file (#771024)

* Sat Mar 31 2012 Adam Williamson <awilliam@redhat.com> - 2.2.22-3
- rebuild against openssl 1.0.0h (previous build was against
  1.0.1, this is not good) RH #808793

* Mon Feb 13 2012 Joe Orton <jorton@redhat.com> - 2.2.22-2
- fix build against PCRE 8.30

* Mon Feb 13 2012 Joe Orton <jorton@redhat.com> - 2.2.22-1
- update to 2.2.22

* Fri Feb 10 2012 Petr Pisar <ppisar@redhat.com> - 2.2.21-8
- Rebuild against PCRE 8.30

* Mon Jan 23 2012 Jan Kaluza <jkaluza@redhat.com> - 2.2.21-7
- fix #783629 - start httpd after named

* Mon Jan 16 2012 Joe Orton <jorton@redhat.com> - 2.2.21-6
- complete conversion to systemd, drop init script (#770311)
- fix comments in /etc/sysconfig/httpd (#771024)
- enable PrivateTmp in service file (#781440)
- set LANG=C in /etc/sysconfig/httpd

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.21-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Tue Dec 06 2011 Jan Kaluza <jkaluza@redhat.com> - 2.2.21-4
- fix #751591 - start httpd after remote-fs

* Mon Oct 24 2011 Jan Kaluza <jkaluza@redhat.com> - 2.2.21-3
- allow change state of BalancerMember in mod_proxy_balancer web interface

* Thu Sep 22 2011 Ville Skyttä <ville.skytta@iki.fi> - 2.2.21-2
- Make mmn available as %%{_httpd_mmn}.
- Add .svgz to AddEncoding x-gzip example in httpd.conf.

* Tue Sep 13 2011 Joe Orton <jorton@redhat.com> - 2.2.21-1
- update to 2.2.21

* Mon Sep  5 2011 Joe Orton <jorton@redhat.com> - 2.2.20-1
- update to 2.2.20
- fix MPM stub man page generation

* Wed Aug 10 2011 Jan Kaluza <jkaluza@redhat.com> - 2.2.19-5
- fix #707917 - add httpd-ssl-pass-dialog to ask for SSL password using systemd

* Fri Jul 22 2011 Iain Arnell <iarnell@gmail.com> 1:2.2.19-4
- rebuild while rpm-4.9.1 is untagged to remove trailing slash in provided
  directory names

* Wed Jul 20 2011 Jan Kaluza <jkaluza@redhat.com> - 2.2.19-3
- fix #716621 - suexec now works without setuid bit

* Thu Jul 14 2011 Jan Kaluza <jkaluza@redhat.com> - 2.2.19-2
- fix #689091 - backported patch from 2.3 branch to support IPv6 in logresolve

* Fri Jul  1 2011 Joe Orton <jorton@redhat.com> - 2.2.19-1
- update to 2.2.19
- enable dbd, authn_dbd in default config

* Thu Apr 14 2011 Joe Orton <jorton@redhat.com> - 2.2.17-13
- fix path expansion in service files

* Tue Apr 12 2011 Joe Orton <jorton@redhat.com> - 2.2.17-12
- add systemd service files (#684175, thanks to Jóhann B. Guðmundsson)

* Wed Mar 23 2011 Joe Orton <jorton@redhat.com> - 2.2.17-11
- minor updates to httpd.conf
- drop old patches

* Wed Mar  2 2011 Joe Orton <jorton@redhat.com> - 2.2.17-10
- rebuild

* Wed Feb 23 2011 Joe Orton <jorton@redhat.com> - 2.2.17-9
- use arch-specific mmn

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.17-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Mon Jan 31 2011 Joe Orton <jorton@redhat.com> - 2.2.17-7
- generate dummy mod_ssl cert with CA:FALSE constraint (#667841)
- add man page stubs for httpd.event, httpd.worker
- drop distcache support
- add STOP_TIMEOUT support to init script

* Sat Jan  8 2011 Joe Orton <jorton@redhat.com> - 2.2.17-6
- update default SSLCipherSuite per upstream trunk

* Wed Jan  5 2011 Joe Orton <jorton@redhat.com> - 2.2.17-5
- fix requires (#667397)

* Wed Jan  5 2011 Joe Orton <jorton@redhat.com> - 2.2.17-4
- de-ghost /var/run/httpd

* Tue Jan  4 2011 Joe Orton <jorton@redhat.com> - 2.2.17-3
- add tmpfiles.d configuration, ghost /var/run/httpd (#656600)

* Sat Nov 20 2010 Joe Orton <jorton@redhat.com> - 2.2.17-2
- drop setuid bit, use capabilities for suexec binary

* Wed Oct 27 2010 Joe Orton <jorton@redhat.com> - 2.2.17-1
- update to 2.2.17

* Fri Sep 10 2010 Joe Orton <jorton@redhat.com> - 2.2.16-2
- link everything using -z relro and -z now

* Mon Jul 26 2010 Joe Orton <jorton@redhat.com> - 2.2.16-1
- update to 2.2.16

* Fri Jul  9 2010 Joe Orton <jorton@redhat.com> - 2.2.15-3
- default config tweaks:
 * harden httpd.conf w.r.t. .htaccess restriction (#591293)
 * load mod_substitute, mod_version by default
 * drop proxy_ajp.conf, load mod_proxy_ajp in httpd.conf
 * add commented list of shipped-but-unloaded modules
 * bump up worker defaults a little
 * drop KeepAliveTimeout to 5 secs per upstream
- fix LSB compliance in init script (#522074)
- bundle NOTICE in -tools
- use init script in logrotate postrotate to pick up PIDFILE
- drop some old Obsoletes/Conflicts

* Sun Apr 04 2010 Robert Scheck <robert@fedoraproject.org> - 2.2.15-1
- update to 2.2.15 (#572404, #579311)

* Thu Dec  3 2009 Joe Orton <jorton@redhat.com> - 2.2.14-1
- update to 2.2.14
- relax permissions on /var/run/httpd (#495780)
- Requires(pre): httpd in mod_ssl subpackage (#543275)
- add partial security fix for CVE-2009-3555 (#533125)

* Tue Oct 27 2009 Tom "spot" Callaway <tcallawa@redhat.com> 2.2.13-4
- add additional explanatory text to test page to help prevent legal emails to Fedora

* Tue Sep  8 2009 Joe Orton <jorton@redhat.com> 2.2.13-2
- restart service in posttrans (#491567)

* Fri Aug 21 2009 Tomas Mraz <tmraz@redhat.com> - 2.2.13-2
- rebuilt with new openssl

* Tue Aug 18 2009 Joe Orton <jorton@redhat.com> 2.2.13-1
- update to 2.2.13

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.11-10
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Tue Jun 16 2009 Joe Orton <jorton@redhat.com> 2.2.11-9
- build -manual as noarch

* Tue Mar 17 2009 Joe Orton <jorton@redhat.com> 2.2.11-8
- fix pidfile in httpd.logrotate (thanks to Rainer Traut)
- don't build mod_mem_cache or mod_file_cache

* Tue Feb 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.11-7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Thu Jan 22 2009 Joe Orton <jorton@redhat.com> 2.2.11-6
- Require: apr-util-ldap (#471898)
- init script changes: pass pidfile to status(), use status() in
  condrestart (#480602), support try-restart as alias for
  condrestart
- change /etc/httpd/run symlink to have destination /var/run/httpd,
  and restore "run/httpd.conf" as default PidFile (#478688)

* Fri Jan 16 2009 Tomas Mraz <tmraz@redhat.com> 2.2.11-5
- rebuild with new openssl

* Sat Dec 27 2008 Robert Scheck <robert@fedoraproject.org> 2.2.11-4
- Made default configuration using /var/run/httpd for pid file

* Thu Dec 18 2008 Joe Orton <jorton@redhat.com> 2.2.11-3
- update to 2.2.11
- package new /var/run/httpd directory, and move default pidfile
  location inside there

* Tue Oct 21 2008 Joe Orton <jorton@redhat.com> 2.2.10-2
- update to 2.2.10

* Tue Jul 15 2008 Joe Orton <jorton@redhat.com> 2.2.9-5
- move AddTypes for SSL cert/CRL types from ssl.conf to httpd.conf (#449979)

* Mon Jul 14 2008 Joe Orton <jorton@redhat.com> 2.2.9-4
- use Charset=UTF-8 in default httpd.conf (#455123)
- only enable suexec when appropriate (Jim Radford, #453697)

* Thu Jul 10 2008 Tom "spot" Callaway <tcallawa@redhat.com>  2.2.9-3
- rebuild against new db4 4.7

* Tue Jul  8 2008 Joe Orton <jorton@redhat.com> 2.2.9-2
- update to 2.2.9
- build event MPM too

* Wed Jun  4 2008 Joe Orton <jorton@redhat.com> 2.2.8-4
- correct UserDir directive in default config (#449815)

* Tue Feb 19 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 2.2.8-3
- Autorebuild for GCC 4.3

* Tue Jan 22 2008 Joe Orton <jorton@redhat.com> 2.2.8-2
- update to 2.2.8
- drop mod_imagemap

* Wed Dec 05 2007 Release Engineering <rel-eng at fedoraproject dot org> - 2.2.6-4
 - Rebuild for openssl bump

* Mon Sep 17 2007 Joe Orton <jorton@redhat.com> 2.2.6-3
- add fix for SSL library string regression (PR 43334)
- use powered-by logo from system-logos (#250676)
- preserve timestamps for installed config files

* Fri Sep  7 2007 Joe Orton <jorton@redhat.com> 2.2.6-2
- update to 2.2.6 (#250757, #282761)

* Sun Sep  2 2007 Joe Orton <jorton@redhat.com> 2.2.4-10
- rebuild for fixed APR

* Wed Aug 22 2007 Joe Orton <jorton@redhat.com> 2.2.4-9
- rebuild for expat soname bump

* Tue Aug 21 2007 Joe Orton <jorton@redhat.com> 2.2.4-8
- fix License
- require /etc/mime.types (#249223)

* Thu Jul 26 2007 Joe Orton <jorton@redhat.com> 2.2.4-7
- drop -tools dependency on httpd (thanks to Matthias Saou)

* Wed Jul 25 2007 Joe Orton <jorton@redhat.com> 2.2.4-6
- split out utilities into -tools subpackage, based on patch
  by Jason Tibbs (#238257)

* Tue Jul 24 2007 Joe Orton <jorton@redhat.com> 2.2.4-5
- spec file cleanups: provide httpd-suexec, mod_dav;
 don't obsolete mod_jk; drop trailing dots from Summaries
- init script
 * add LSB info header, support force-reload (#246944)
 * update description
 * drop 1.3 config check
 * pass $pidfile to daemon and pidfile everywhere

* Wed May  9 2007 Joe Orton <jorton@redhat.com> 2.2.4-4
- update welcome page branding

* Tue Apr  3 2007 Joe Orton <jorton@redhat.com> 2.2.4-3
- drop old triggers, old Requires, xmlto BR
- use Requires(...) correctly
- use standard BuildRoot
- don't mark init script as config file
- trim CHANGES further

* Mon Mar 12 2007 Joe Orton <jorton@redhat.com> 2.2.4-2
- update to 2.2.4
- drop the migration guide (#223605)

* Thu Dec  7 2006 Joe Orton <jorton@redhat.com> 2.2.3-8
- fix path to instdso.sh in special.mk (#217677)
- fix detection of links in "apachectl fullstatus"

* Tue Dec  5 2006 Joe Orton <jorton@redhat.com> 2.2.3-7
- rebuild for libpq soname bump

* Sat Nov 11 2006 Joe Orton <jorton@redhat.com> 2.2.3-6
- rebuild for BDB soname bump

* Mon Sep 11 2006 Joe Orton <jorton@redhat.com> 2.2.3-5
- updated "powered by Fedora" logo (#205573, Diana Fong)
- tweak welcome page wording slightly (#205880)

* Fri Aug 18 2006 Jesse Keating <jkeating@redhat.com> - 2.2.3-4
- rebuilt with latest binutils to pick up 64K -z commonpagesize on ppc*
  (#203001)

* Thu Aug  3 2006 Joe Orton <jorton@redhat.com> 2.2.3-3
- init: use killproc() delay to avoid race killing parent

* Fri Jul 28 2006 Joe Orton <jorton@redhat.com> 2.2.3-2
- update to 2.2.3
- trim %%changelog to >=2.0.52

* Thu Jul 20 2006 Joe Orton <jorton@redhat.com> 2.2.2-8
- fix segfault on dummy connection failure at graceful restart (#199429)

* Wed Jul 19 2006 Joe Orton <jorton@redhat.com> 2.2.2-7
- fix "apxs -g"-generated Makefile
- fix buildconf with autoconf 2.60

* Wed Jul 12 2006 Jesse Keating <jkeating@redhat.com> - 2.2.2-5.1
- rebuild

* Wed Jun  7 2006 Joe Orton <jorton@redhat.com> 2.2.2-5
- require pkgconfig for -devel (#194152)
- fixes for installed support makefiles (special.mk et al)
- BR autoconf

* Fri Jun  2 2006 Joe Orton <jorton@redhat.com> 2.2.2-4
- make -devel package multilib-safe (#192686)

* Thu May 11 2006 Joe Orton <jorton@redhat.com> 2.2.2-3
- build DSOs using -z relro linker flag

* Wed May  3 2006 Joe Orton <jorton@redhat.com> 2.2.2-2
- update to 2.2.2

* Thu Apr  6 2006 Joe Orton <jorton@redhat.com> 2.2.0-6
- rebuild to pick up apr-util LDAP interface fix (#188073)

* Fri Feb 10 2006 Jesse Keating <jkeating@redhat.com> - (none):2.2.0-5.1.2
- bump again for double-long bug on ppc(64)

* Tue Feb 07 2006 Jesse Keating <jkeating@redhat.com> - (none):2.2.0-5.1.1
- rebuilt for new gcc4.1 snapshot and glibc changes

* Mon Feb  6 2006 Joe Orton <jorton@redhat.com> 2.2.0-5.1
- mod_auth_basic/mod_authn_file: if no provider is configured,
  and AuthUserFile is not configured, decline to handle authn
  silently rather than failing noisily.

* Fri Feb  3 2006 Joe Orton <jorton@redhat.com> 2.2.0-5
- mod_ssl: add security fix for CVE-2005-3357 (#177914)
- mod_imagemap: add security fix for CVE-2005-3352 (#177913)
- add fix for AP_INIT_* designated initializers with C++ compilers
- httpd.conf: enable HTMLTable in default IndexOptions
- httpd.conf: add more "redirect-carefully" matches for DAV clients

* Thu Jan  5 2006 Joe Orton <jorton@redhat.com> 2.2.0-4
- mod_proxy_ajp: fix Cookie handling (Mladen Turk, r358769)

* Fri Dec 09 2005 Jesse Keating <jkeating@redhat.com>
- rebuilt

* Wed Dec  7 2005 Joe Orton <jorton@redhat.com> 2.2.0-3
- strip manual to just English content

* Mon Dec  5 2005 Joe Orton <jorton@redhat.com> 2.2.0-2
- don't strip C-L from HEAD responses (Greg Ames, #110552)
- load mod_proxy_balancer by default
- add proxy_ajp.conf to load/configure mod_proxy_ajp
- Obsolete mod_jk
- update docs URLs in httpd.conf/ssl.conf

* Fri Dec  2 2005 Joe Orton <jorton@redhat.com> 2.2.0-1
- update to 2.2.0

* Wed Nov 30 2005 Joe Orton <jorton@redhat.com> 2.1.10-2
- enable mod_authn_alias, mod_authn_anon
- update default httpd.conf

* Fri Nov 25 2005 Joe Orton <jorton@redhat.com> 2.1.10-1
- update to 2.1.10
- require apr >= 1.2.0, apr-util >= 1.2.0

* Wed Nov  9 2005 Tomas Mraz <tmraz@redhat.com> 2.0.54-16
- rebuilt against new openssl

* Thu Nov  3 2005 Joe Orton <jorton@redhat.com> 2.0.54-15
- log notice giving SELinux context at startup if enabled
- drop SSLv2 and restrict default cipher suite in default
 SSL configuration

* Thu Oct 20 2005 Joe Orton <jorton@redhat.com> 2.0.54-14
- mod_ssl: add security fix for SSLVerifyClient (CVE-2005-2700)
- add security fix for byterange filter DoS (CVE-2005-2728)
- add security fix for C-L vs T-E handling (CVE-2005-2088)
- mod_ssl: add security fix for CRL overflow (CVE-2005-1268)
- mod_ldap/mod_auth_ldap: add fixes from 2.0.x branch (upstream #34209 etc)
- add fix for dummy connection handling (#167425)
- mod_auth_digest: fix hostinfo comparison in CONNECT requests
- mod_include: fix variable corruption in nested includes (upstream #12655)
- mod_ssl: add fix for handling non-blocking reads
- mod_ssl: fix to enable output buffering (upstream #35279)
- mod_ssl: buffer request bodies for per-location renegotiation (upstream #12355)

* Sat Aug 13 2005 Joe Orton <jorton@redhat.com> 2.0.54-13
- don't load by default: mod_cern_meta, mod_asis
- do load by default: mod_ext_filter (#165893)

* Thu Jul 28 2005 Joe Orton <jorton@redhat.com> 2.0.54-12
- drop broken epoch deps

* Thu Jun 30 2005 Joe Orton <jorton@redhat.com> 2.0.54-11
- mod_dav_fs: fix uninitialized variable (#162144)
- add epoch to dependencies as appropriate
- mod_ssl: drop dependencies on dev, make
- mod_ssl: mark post script dependencies as such

* Mon May 23 2005 Joe Orton <jorton@redhat.com> 2.0.54-10
- remove broken symlink (Robert Scheck, #158404)

* Wed May 18 2005 Joe Orton <jorton@redhat.com> 2.0.54-9
- add piped logger fixes (w/Jeff Trawick)

* Mon May  9 2005 Joe Orton <jorton@redhat.com> 2.0.54-8
- drop old "powered by Red Hat" logos

* Wed May  4 2005 Joe Orton <jorton@redhat.com> 2.0.54-7
- mod_userdir: fix memory allocation issue (upstream #34588)
- mod_ldap: fix memory corruption issue (Brad Nicholes, upstream #34618)

* Tue Apr 26 2005 Joe Orton <jorton@redhat.com> 2.0.54-6
- fix key/cert locations in post script

* Mon Apr 25 2005 Joe Orton <jorton@redhat.com> 2.0.54-5
- create default dummy cert in /etc/pki/tls
- use a pseudo-random serial number on the dummy cert
- change default ssl.conf to point at /etc/pki/tls
- merge back -suexec subpackage; SELinux policy can now be
  used to persistently disable suexec (#155716)
- drop /etc/httpd/conf/ssl.* directories and Makefiles
- unconditionally enable PIE support
- mod_ssl: fix for picking up -shutdown options (upstream #34452)

* Mon Apr 18 2005 Joe Orton <jorton@redhat.com> 2.0.54-4
- replace PreReq with Requires(pre)

* Mon Apr 18 2005 Joe Orton <jorton@redhat.com> 2.0.54-3
- update to 2.0.54

* Tue Mar 29 2005 Joe Orton <jorton@redhat.com> 2.0.53-6
- update default httpd.conf:
 * clarify the comments on AddDefaultCharset usage (#135821)
 * remove all the AddCharset default extensions
 * don't load mod_imap by default
 * synch with upstream 2.0.53 httpd-std.conf
- mod_ssl: set user from SSLUserName in access hook (upstream #31418)
- htdigest: fix permissions of created files (upstream #33765)
- remove htsslpass

* Wed Mar  2 2005 Joe Orton <jorton@redhat.com> 2.0.53-5
- apachectl: restore use of $OPTIONS again

* Wed Feb  9 2005 Joe Orton <jorton@redhat.com> 2.0.53-4
- update to 2.0.53
- move prefork/worker modules comparison to %%check

* Mon Feb  7 2005 Joe Orton <jorton@redhat.com> 2.0.52-7
- fix cosmetic issues in "service httpd reload"
- move User/Group higher in httpd.conf (#146793)
- load mod_logio by default in httpd.conf
- apachectl: update for correct libselinux tools locations

* Tue Nov 16 2004 Joe Orton <jorton@redhat.com> 2.0.52-6
- add security fix for CVE CAN-2004-0942 (memory consumption DoS)
- SELinux: run httpd -t under runcon in configtest (Steven Smalley)
- fix SSLSessionCache comment for distcache in ssl.conf
- restart using SIGHUP not SIGUSR1 after logrotate
- add ap_save_brigade fix (upstream #31247)
- mod_ssl: fix possible segfault in auth hook (upstream #31848)
- add htsslpass(1) and configure as default SSLPassPhraseDialog (#128677)
- apachectl: restore use of $OPTIONS
- apachectl, httpd.init: refuse to restart if $HTTPD -t fails
- apachectl: run $HTTPD -t in user SELinux context for configtest
- update for pcre-5.0 header locations

* Sat Nov 13 2004 Jeff Johnson <jbj@redhat.com> 2.0.52-5
- rebuild against db-4.3.21 aware apr-util.

* Thu Nov 11 2004 Jeff Johnson <jbj@jbj.org> 2.0.52-4
- rebuild against db-4.3-21.

* Tue Sep 28 2004 Joe Orton <jorton@redhat.com> 2.0.52-3
- add dummy connection address fixes from HEAD
- mod_ssl: add security fix for CAN-2004-0885

* Tue Sep 28 2004 Joe Orton <jorton@redhat.com> 2.0.52-2
- update to 2.0.52

