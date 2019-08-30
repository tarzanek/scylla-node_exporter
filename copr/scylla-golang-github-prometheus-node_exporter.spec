# If any of the following macros should be set otherwise,
# you can wrap any of them with the following conditions:
# - %%if 0%%{centos} == 7
# - %%if 0%%{?rhel} == 7
# - %%if 0%%{?fedora} == 23
# Or just test for particular distribution:
# - %%if 0%%{centos}
# - %%if 0%%{?rhel}
# - %%if 0%%{?fedora}
#
# Be aware, on centos, both %%rhel and %%centos are set. If you want to test
# rhel specific macros, you can use %%if 0%%{?rhel} && 0%%{?centos} == 0 condition.
# (Don't forget to replace double percentage symbol with single one in order to apply a condition)

# Generate devel rpm
%global with_devel 0
# Build project from bundled dependencies
%global with_bundled 1
# Build with debug info rpm
%global with_debug 0
# Run tests in check section
%global with_check 1
# Generate unit-test rpm
%global with_unit_test 0

%if 0%{?with_debug}
%global _dwz_low_mem_die_limit 0
%else
%global debug_package   %{nil}
%endif


%global provider        github
%global provider_tld    com
%global project         prometheus
%global repo            node_exporter
# https://github.com/prometheus/node_exporter
%global provider_prefix %{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path     %{provider_prefix}
#%global commit          0e60bb8e005c638605e59ac3f307e3d47e891a9f
#%global shortcommit     %(c=%{commit}; echo ${c:0:7})

%global scylladir /opt/scylladb

Name:           scylla-%{repo}
Version:        0.17.0
Release:        6%{?dist}
Summary:        Exporter for machine metrics
License:        AGPL 3.0
URL:            https://%{provider_prefix}
#Source0:        https://%{provider_prefix}/archive/%{commit}/%{repo}-%{shortcommit}.tar.gz
Source0:        https://%{provider_prefix}/archive/v%{version}.tar.gz
Source1:        scylla-node_exporter.service

Provides:       scylla-node_exporter = %{version}-%{release}

%if 0%{?rhel} != 6
BuildRequires:  systemd
%endif

# e.g. el6 has ppc64 arch without gcc-go, so EA tag is required
ExclusiveArch:  %{?go_arches:%{go_arches}}%{!?go_arches:%{ix86} x86_64 aarch64 %{arm}}
# If go_compiler is not set to 1, there is no virtual provide. Use golang instead.
BuildRequires:  %{?go_compiler:compiler(go-compiler)}%{!?go_compiler:golang}

%description
%{summary}

%if 0%{?with_devel}
%package devel
Summary:       %{summary}
BuildArch:     noarch

BuildRequires: git
%if 0%{?with_check} && ! 0%{?with_bundled}
BuildRequires: golang(github.com/beevik/ntp)
BuildRequires: golang(github.com/coreos/go-systemd/dbus)
BuildRequires: golang(github.com/godbus/dbus)
BuildRequires: golang(github.com/golang/protobuf/proto)
BuildRequires: golang(github.com/kolo/xmlrpc)
BuildRequires: golang(github.com/mdlayher/wifi)
BuildRequires: golang(github.com/prometheus/client_golang/prometheus)
BuildRequires: golang(github.com/prometheus/client_model/go)
BuildRequires: golang(github.com/prometheus/common/expfmt)
BuildRequires: golang(github.com/prometheus/common/log)
BuildRequires: golang(github.com/prometheus/procfs)
BuildRequires: golang(github.com/soundcloud/go-runit/runit)
BuildRequires: golang(golang.org/x/sys/unix)
%endif

Requires:      golang(github.com/beevik/ntp)
Requires:      golang(github.com/coreos/go-systemd/dbus)
Requires:      golang(github.com/godbus/dbus)
Requires:      golang(github.com/golang/protobuf/proto)
Requires:      golang(github.com/kolo/xmlrpc)
Requires:      golang(github.com/mdlayher/wifi)
Requires:      golang(github.com/prometheus/client_golang/prometheus)
Requires:      golang(github.com/prometheus/client_model/go)
Requires:      golang(github.com/prometheus/common/expfmt)
Requires:      golang(github.com/prometheus/common/log)
Requires:      golang(github.com/prometheus/procfs)
Requires:      golang(github.com/soundcloud/go-runit/runit)
Requires:      golang(golang.org/x/sys/unix)

Provides:      golang(%{import_path}/collector) = %{version}-%{release}
Provides:      golang(%{import_path}/collector/ganglia) = %{version}-%{release}

%description devel
%{summary}

This package contains node_exporter source intended for
building other packages which use import path with
%{import_path} prefix.
%endif

%if 0%{?with_unit_test} && 0%{?with_devel}
%package unit-test-devel
Summary:         Unit tests for %{name} package
%if 0%{?with_check}
#Here comes all BuildRequires: PACKAGE the unit tests
#in %%check section need for running
%endif

# test subpackage tests code from devel subpackage
Requires:        %{name}-devel = %{version}-%{release}

%if 0%{?with_check} && ! 0%{?with_bundled}
BuildRequires: golang(github.com/prometheus/client_golang/prometheus/promhttp)
%endif

Requires:      golang(github.com/prometheus/client_golang/prometheus/promhttp)

%description unit-test-devel
%{summary}

This package contains unit tests for project
providing packages with %{import_path} prefix.
%endif

%prep
%setup -q -n %{repo}-%{version}

%build
mkdir -p _build/src/%{provider}.%{provider_tld}/%{project}
ln -s $(pwd) _build/src/%{provider_prefix}

%if ! 0%{?with_bundled}
export GOPATH=$(pwd)/_build:%{gopath}
%else
# Since we aren't packaging up the vendor directory we need to link
# back to it somehow. Hack it up so that we can add the vendor
# directory from BUILD dir as a gopath to be searched when executing
# tests from the BUILDROOT dir.
ln -s ./ ./vendor/src # ./vendor/src -> ./vendor
export GOPATH=$(pwd)/_build:$(pwd)/vendor:%{gopath}
%endif

# set version information
export LDFLAGS="-X github.com/prometheus/common/version.Version=%{version} -X github.com/prometheus/common/version.BuildUser=copr -X github.com/prometheus/common/version.BuildDate=$(date '+%Y%m%d-%T')"

%if ! 0%{?gobuild:1}
function _gobuild { go build -a -ldflags "-B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \n') $LDFLAGS" -v -x "$@"; }
%global gobuild _gobuild
%endif

# below is due to bug https://github.com/prometheus/node_exporter/issues/1420
echo "
50c50
< github.com/soundcloud/go-runit v0.0.0-20150630195641-06ad41a06c4a h1:TGsOnmXp0mo82KbjaDcsTibGxWIdZNXbKJB18gFn1RM=
---
> github.com/soundcloud/go-runit v0.0.0-20150630195641-06ad41a06c4a h1:os5OBNhwOwybXZMNLqT96XqtjdTtwRFw2w08uluvNeI=
" > patch.go.sum

patch go.sum < patch.go.sum

%gobuild -o _build/node_exporter %{provider_prefix}

%install
install -d -p   %{buildroot}/%{scylladir}/bin
#                %{buildroot}/%{scylladir}/%{_defaultdocdir}/node_exporter

%if 0%{?rhel} != 6
install -d -p   %{buildroot}/%{_unitdir}
%endif

%if 0%{?rhel} != 6
install -p -m 0644 %{_sourcedir}/scylla-node_exporter.service %{buildroot}/%{_unitdir}/scylla-node_exporter.service
%endif
install -p -m 0755 ./_build/node_exporter %{buildroot}/%{scylladir}/bin/node_exporter

# source codes for building projects
%if 0%{?with_devel}
install -d -p %{buildroot}/%{scylladir}/%{gopath}/src/%{import_path}/
echo "%%dir %%{gopath}/src/%%{import_path}/." >> devel.file-list
# find all *.go but no *_test.go files and generate devel.file-list
for file in $(find . \( -iname "*.go" -or -iname "*.s" \) \! -iname "*_test.go" | grep -v "vendor") ; do
    dirprefix=$(dirname $file)
    install -d -p %{buildroot}/%{scylladir}/%{gopath}/src/%{import_path}/$dirprefix
    cp -pav $file %{buildroot}/%{scylladir}/%{gopath}/src/%{import_path}/$file
    echo "%%{gopath}/src/%%{import_path}/$file" >> devel.file-list

    while [ "$dirprefix" != "." ]; do
        echo "%%dir %%{gopath}/src/%%{import_path}/$dirprefix" >> devel.file-list
        dirprefix=$(dirname $dirprefix)
    done
done
%endif

# testing files for this project
%if 0%{?with_unit_test} && 0%{?with_devel}
install -d -p %{buildroot}/%{scylladir}/%{gopath}/src/%{import_path}/
# find all *_test.go files and generate unit-test-devel.file-list
for file in $(find . -iname "*_test.go" | grep -v "vendor") ; do
    dirprefix=$(dirname $file)
    install -d -p %{buildroot}/%{scylladir}/%{gopath}/src/%{import_path}/$dirprefix
    cp -pav $file %{buildroot}/%{scylladir}/%{gopath}/src/%{import_path}/$file
    echo "%%{gopath}/src/%%{import_path}/$file" >> unit-test-devel.file-list

    while [ "$dirprefix" != "." ]; do
        echo "%%dir %%{gopath}/src/%%{import_path}/$dirprefix" >> devel.file-list
        dirprefix=$(dirname $dirprefix)
    done
done
%endif

%if 0%{?with_devel}
sort -u -o devel.file-list devel.file-list
%endif

%check
%if 0%{?with_check} && 0%{?with_unit_test} && 0%{?with_devel}
%if ! 0%{?with_bundled}
export GOPATH=%{buildroot}/%{scylladir}/%{gopath}:%{gopath}
%else
# Since we aren't packaging up the vendor directory we need to link
# back to it somehow. Hack it up so that we can add the vendor
# directory from BUILD dir as a gopath to be searched when executing
# tests from the BUILDROOT dir.
ln -s ./ ./vendor/src # ./vendor/src -> ./vendor

export GOPATH=%{buildroot}/%{scylladir}/%{gopath}:$(pwd)/vendor:%{gopath}
%endif

%if ! 0%{?gotest:1}
%global gotest go test
%endif

%gotest %{import_path}
%gotest %{import_path}/collector
%endif

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%if 0%{?with_devel}
%files devel -f devel.file-list
%dir %{gopath}/src/%{provider}.%{provider_tld}/%{project}
%endif

%if 0%{?with_unit_test} && 0%{?with_devel}
%files unit-test-devel -f unit-test-devel.file-list
%endif

%files
%if 0%{?rhel} != 6
%{_unitdir}/scylla-node_exporter.service
%endif
%license LICENSE
%{scylladir}/*

%pre

%post
%if 0%{?rhel} != 6
%systemd_post scylla-node_exporter.service
%endif

%preun
%if 0%{?rhel} != 6
%systemd_preun scylla-node_exporter.service
%endif

%postun
%if 0%{?rhel} != 6
%systemd_postun scylla-node_exporter.service
%endif

%changelog
* Mon Aug 05 2019 Lubos Kosco <tarzanek@gmail.com> 0.17.0
- initial scylla packaging

