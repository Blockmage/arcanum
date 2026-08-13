from collections.abc import Iterator
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    IPv6Address,
    IPv6Interface,
    IPv6Network,
    collapse_addresses,
    ip_address,
    ip_interface,
    ip_network,
)
from typing import Any, Literal, Self, cast

# ruff: noqa: D205 (missing-blank-line-after-summary)

__all__ = (
    'IPAddress',
    'IPInterface',
    'IPNetwork',
    'RawIPAddress',
    'RawNetworkPart',
)

type RawIPAddress = int | str | bytes | IPv4Address | IPv6Address
type RawNetworkPart = IPv4Network | IPv6Network | IPv4Interface | IPv6Interface


class _IPObject:
    """Base class for common IP address, network, and interface properties."""

    __slots__ = ()

    @property
    def version(self) -> Literal[4, 6]:
        """IP version (either `4` or `6`)."""
        raise NotImplementedError

    @property
    def is_multicast(self) -> bool:
        """`True` if the address/network is reserved for multicast use."""
        raise NotImplementedError

    @property
    def is_private(self) -> bool:
        """`True` if the address/network is defined as *not globally reachable*."""
        raise NotImplementedError

    @property
    def is_global(self) -> bool:
        """`True` if the address/network is defined as *globally reachable*."""
        raise NotImplementedError

    @property
    def is_reserved(self) -> bool:
        """`True` if the address/network is noted as reserved by the IETF."""
        raise NotImplementedError

    @property
    def is_loopback(self) -> bool:
        """`True` if this is a loopback address/network."""
        raise NotImplementedError

    @property
    def is_link_local(self) -> bool:
        """`True` if the address/network falls within the link-local scope."""
        raise NotImplementedError

    @property
    def is_unspecified(self) -> bool:
        """`True` if the address/network is unspecified."""
        raise NotImplementedError


class IPAddress(_IPObject):
    """General-purpose IP address wrapper.

    Unifies `ipaddress.IPv4Address` and `ipaddress.IPv6Address` to a single type.
    """

    __slots__ = ('_address',)

    @classmethod
    def __msgspec_decode__(cls, obj: Any) -> Self:
        return cls(obj)

    def __msgspec_encode__(self) -> str:
        return str(self)

    def __init__(self, address: RawIPAddress, /) -> None:
        """Initialize an instance of `IPAddress`.

        Parameters
        ----------
        address : RawIPAddress
            IP address. Will be coerced into the appropriate `ipaddress.IPv4Address` or `ipaddress.IPv6Address` object
            instance by the class internally.

        Raises
        ------
        ipaddress.AddressValueError
            If `address` is not a valid IPv4 or IPv6 address.
        """
        self._address = ip_address(address)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._address!s})'

    def __str__(self) -> str:
        return str(self._address)

    def __int__(self) -> int:
        return int(self._address)

    def __hash__(self) -> int:
        return hash(self._address)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, IPAddress):
            return self._address == other._address
        if isinstance(other, (IPv4Address, IPv6Address)):
            return self._address == other
        if isinstance(other, (str, int, bytes)):
            try:
                return self._address == ip_address(other)
            except (ValueError, TypeError):
                return False
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, IPAddress):
            return self._sort_key() < other._sort_key()
        if isinstance(other, (IPv4Address, IPv6Address)):
            return self._sort_key() < (other.version, int(other))
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, IPAddress):
            return self._sort_key() <= other._sort_key()
        if isinstance(other, (IPv4Address, IPv6Address)):
            return self._sort_key() <= (other.version, int(other))
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, IPAddress):
            return self._sort_key() > other._sort_key()
        if isinstance(other, (IPv4Address, IPv6Address)):
            return self._sort_key() > (other.version, int(other))
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, IPAddress):
            return self._sort_key() >= other._sort_key()
        if isinstance(other, (IPv4Address, IPv6Address)):
            return self._sort_key() >= (other.version, int(other))
        return NotImplemented

    def _sort_key(self) -> tuple[int, int]:
        """Return a version-prefixed integer for cross-version comparison."""
        return (self._address.version, int(self._address))

    def unwrap(self) -> IPv4Address | IPv6Address:
        """Return the underlying `ipaddress.IPv4Address` or `ipaddress.IPv6Address`."""
        return self._address

    @property
    def address(self) -> IPv4Address | IPv6Address:
        """An instance of either `ipaddress.IPv4Address` or `ipaddress.IPv6Address`."""
        return self._address

    @property
    def max_prefixlen(self) -> Literal[32, 128]:
        """Either `32` (for IPv4), or `128` (for IPv6)."""
        return self._address.max_prefixlen

    @property
    def version(self) -> Literal[4, 6]:
        """IP version (either `4` or `6`)."""
        return self._address.version

    @property
    def packed(self) -> bytes:
        """Binary representation of the address.

        This is a `bytes` object of `4` bytes length for IPv4, or `16` bytes length for IPv6, with the most significant
        octet first.
        """
        return self._address.packed

    @property
    def compressed(self) -> str:
        """Compressed string representation of the address."""
        return self._address.compressed

    @property
    def exploded(self) -> str:
        """Fully-expanded string representation of the address."""
        return self._address.exploded

    @property
    def reverse_pointer(self) -> str:
        """Reverse DNS PTR record for the address.

        Examples
        --------
        >>> ipaddress.ip_address('127.0.0.1').reverse_pointer
        '1.0.0.127.in-addr.arpa'
        >>> ipaddress.ip_address('2001:db8::1').reverse_pointer
        '1.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2.ip6.arpa'
        """
        return self._address.reverse_pointer

    @property
    def is_ipv4(self) -> bool:
        """`True` if the wrapped address is an IPv4 address."""
        return self.version == 4

    @property
    def is_ipv6(self) -> bool:
        """`True` if the wrapped address is an IPv6 address."""
        return self.version == 6

    @property
    def is_multicast(self) -> bool:
        """`True` if the address is reserved for multicast use.

        Notes
        -----
        - See [**RFC 3171**](https://datatracker.ietf.org/doc/html/rfc3171.html) (for IPv4) or
          [**RFC 2373**](https://datatracker.ietf.org/doc/html/rfc2373.html) (for IPv6).
        """
        return self._address.is_multicast

    @property
    def is_site_local(self) -> bool:
        """`True` if this is an IPv6 address which is reserved for site-local usage.

        Notes
        -----
        - The site-local address space has been deprecated by
          [**RFC 3879**](https://datatracker.ietf.org/doc/html/rfc3879.html).

          Use `is_private` to test if this address is in the space of unique local addresses as defined by
          [**RFC 4193**](https://datatracker.ietf.org/doc/html/rfc4193.html).
        """
        return isinstance(self._address, IPv6Address) and self._address.is_site_local

    @property
    def is_private(self) -> bool:
        """`True` if the address is defined as *not globally reachable* by the
        [**IANA IPv4 Special Registry**](https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml)
        (for IPv4) or
        [**IANA IPv6 Special Registry**](https://www.iana.org/assignments/iana-ipv6-special-registry/iana-ipv6-special-registry.xhtml)
        (for IPv6).

        Notes
        -----
        - `is_private` is `False` for the shared address space (`100.64.0.0/10`)
        - For IPv4-mapped IPv6-addresses, the value of `is_private` is determined by the semantics of the underlying
          IPv4 addresses, and the following condition holds (see `ipaddress.IPv6Address.ipv4_mapped`):

          ```python
          address.is_private == address.ipv4_mapped.is_private
          ```

        - `is_private` has value opposite to `is_global`, with the exception of the shared address space
          (`100.64.0.0/10`), within which they are both `False`.
        - `192.0.0.0/24` is considered private, with the exception of `192.0.0.9/32` and `192.0.0.10/32`.
        - `64:ff9b:1::/48` is considered private.
        - `2002::/16` is considered private.
        - There are exceptions within `2001::/23` (which is otherwise considered private); the following are **not**
          considered private:
            - `2001:1::1/128`
            - `2001:1::2/128`
            - `2001:3::/32`
            - `2001:4:112::/48`
            - `2001:20::/28`
            - `2001:30::/28`
        """
        return self._address.is_private

    @property
    def is_global(self) -> bool:
        """`True` if the address is defined as *globally reachable* by the
        [**IANA IPv4 Special Registry**](https://iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml)
        (for IPv4) or
        [**IANA IPv6 Special Registry**](https://iana.org/assignments/iana-ipv6-special-registry/iana-ipv6-special-registry.xhtml)
        (for IPv6).

        Notes
        -----
        - `is_global` has value opposite to `is_private`, with the exception of the shared address space
          (`100.64.0.0/10`), within which they are both `False`.
        - For IPv4-mapped IPv6-addresses, the value of `is_private` is determined by the semantics of the underlying
          IPv4 addresses, and the following condition holds (see `ipaddress.IPv6Address.ipv4_mapped`):

          ```python
          address.is_global == address.ipv4_mapped.is_global
          ```
        """
        return self._address.is_global

    @property
    def is_reserved(self) -> bool:
        """`True` if the address is noted as reserved by the IETF.

        Notes
        -----
        - For IPv4, this is only `240.0.0.0/4` (the only `Reserved` address block).
        - For IPv4, `is_reserved` is **not** related to the address block value of the `Reserved-by-Protocol` column in
          the [**IANA IPv4 Special Registry**](https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml).
        - For IPv6, this is all addresses [**allocated as `Reserved`**](https://www.iana.org/assignments/ipv6-address-space/ipv6-address-space.xhtml)
          by the IETF for future use.
        - **CAUTION:** For IPv6, `fec0::/10`, a former `Site-Local`-scoped address prefix, is currently excluded from
          that list (see `is_site_local` and [**RFC 3879**](https://datatracker.ietf.org/doc/html/rfc3879.html)).
        """
        return self._address.is_reserved

    @property
    def is_loopback(self) -> bool:
        """`True` if this is a loopback address.

        Notes
        -----
        - See [**RFC 3330**](https://datatracker.ietf.org/doc/html/rfc3330.html) (for IPv4) or
          [**RFC 2373**](https://datatracker.ietf.org/doc/html/rfc2373.html) (for IPv6).
        """
        return self._address.is_loopback

    @property
    def is_link_local(self) -> bool:
        """`True` if the address falls within the link-local scope."""
        return self._address.is_link_local

    @property
    def is_unspecified(self) -> bool:
        """`True` if the address is unspecified.

        Notes
        -----
        - See [**RFC 5735**](https://datatracker.ietf.org/doc/html/rfc5735.html) (for IPv4) or
          [**RFC 2373**](https://datatracker.ietf.org/doc/html/rfc2373.html) (for IPv6).
        """
        return self._address.is_unspecified

    @property
    def ipv6_mapped(self) -> 'IPAddress | None':
        """If this address is an IPv4 address, this property will report the IPv6-mapped representation of the address;
        otherwise, this property will be `None`.

        Notes
        -----
        - See [**RFC 4291 - IP Version 6 Addressing Architecture**](https://datatracker.ietf.org/doc/html/rfc4291.html).
        """
        mapped = getattr(self._address, 'ipv6_mapped', None)
        return IPAddress(mapped) if isinstance(mapped, IPv6Address) else None

    @property
    def ipv4_mapped(self) -> 'IPAddress | None':
        """If this address is an IPv6 address which appears to be a mapped IPv4 address (an address starting with
        `::FFFF/96`), this property will report the embedded IPv4 address; otherwise, this property will be `None`.

        Notes
        -----
        - See [**RFC 4291 - IP Version 6 Addressing Architecture**](https://datatracker.ietf.org/doc/html/rfc4291.html).
        """
        mapped = getattr(self._address, 'ipv4_mapped', None)
        return IPAddress(mapped) if isinstance(mapped, IPv4Address) else None

    @property
    def teredo(self) -> 'tuple[IPAddress, IPAddress] | None':
        """If this address is an IPv6 address which appears to be a Teredo address (an address starting with
        `2001::/32`), this property will report the embedded `(server, client)` IPv4 address pair; otherwise, this
        property will be `None`.

        Notes
        -----
        - See [**RFC 4380 - Teredo: Tunneling IPv6 over UDP through Network Address Translations (NATs)**](https://datatracker.ietf.org/doc/html/rfc4380.html)
        """
        val = getattr(self._address, 'teredo', None)
        if isinstance(val, tuple) and len(val) == 2:
            return (IPAddress(val[0]), IPAddress(val[1]))
        return None

    @property
    def sixtofour(self) -> 'IPAddress | None':
        """If this address is an IPv6 address which appears to be a `6to4` address (an address starting with
        `2002::/16`), this property will report the embedded IPv4 address; otherwise, this property will be `None`.

        Notes
        -----
        - See [**RFC 3056 - Connection of IPv6 Domains via IPv4 Clouds**](https://datatracker.ietf.org/doc/html/rfc3056.html)
        """
        val = getattr(self._address, 'sixtofour', None)
        return IPAddress(val) if isinstance(val, IPv4Address) else None

    @property
    def scope_id(self) -> str | None:
        """If this address is a scoped IPv6 address, this property will report the zone of the address's scope as a
        string; if no scope is defined, or if this is not an IPv6 address, the property will be `None`.

        Notes
        -----
        - See [**RFC 4007 - IPv6 Scoped Address Architecture**](https://datatracker.ietf.org/doc/html/rfc4007.html)
        """
        return getattr(self._address, 'scope_id', None)


class IPInterface(_IPObject):
    """General-purpose IP interface wrapper.

    Unifies `ipaddress.IPv4Interface` and `ipaddress.IPv6Interface` to a single type.
    """

    __slots__ = ('_interface',)

    @classmethod
    def __msgspec_decode__(cls, obj: Any) -> Self:
        return cls(obj)

    def __msgspec_encode__(self) -> str:
        return str(self)

    def __init__(self, address: RawIPAddress | RawNetworkPart | tuple[RawIPAddress] | tuple[RawIPAddress, int]) -> None:
        """Initialize an instance of `IPInterface`.

        Parameters
        ----------
        address : RawIPAddress | RawNetworkPart | tuple[RawIPAddress] | tuple[RawIPAddress, int]
            IP interface address. Will be coerced into the appropriate `ipaddress.IPv4Interface` or
            `ipaddress.IPv6Interface` object instance by the class internally.

        Raises
        ------
        ipaddress.AddressValueError
            If `address` is not a valid IPv4 or IPv6 interface.
        ipaddress.NetmaskValueError
            If the netmask is invalid.
        """
        self._interface = ip_interface(address)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._interface.with_prefixlen!s})'

    def __str__(self) -> str:
        return str(self._interface)

    def __hash__(self) -> int:
        return hash(self._interface)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, IPInterface):
            return self._interface == other._interface
        if isinstance(other, (IPv4Interface, IPv6Interface)):
            return self._interface == other
        if isinstance(other, (str, int, bytes, tuple)):
            try:
                return self._interface == ip_interface(other)
            except (ValueError, TypeError):
                return False
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, IPInterface):
            return self._sort_key() < other._sort_key()
        if isinstance(other, (IPv4Interface, IPv6Interface)):
            return self._sort_key() < (other.version, int(other.ip), other.network.prefixlen)
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, IPInterface):
            return self._sort_key() <= other._sort_key()
        if isinstance(other, (IPv4Interface, IPv6Interface)):
            return self._sort_key() <= (other.version, int(other.ip), other.network.prefixlen)
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, IPInterface):
            return self._sort_key() > other._sort_key()
        if isinstance(other, (IPv4Interface, IPv6Interface)):
            return self._sort_key() > (other.version, int(other.ip), other.network.prefixlen)
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, IPInterface):
            return self._sort_key() >= other._sort_key()
        if isinstance(other, (IPv4Interface, IPv6Interface)):
            return self._sort_key() >= (other.version, int(other.ip), other.network.prefixlen)
        return NotImplemented

    def _sort_key(self) -> tuple[int, int, int]:
        """Return a sort key: (version, address_int, prefixlen)."""
        return (self._interface.version, int(self._interface.ip), self._interface.network.prefixlen)

    def unwrap(self) -> IPv4Interface | IPv6Interface:
        """Return the underlying `IPv4Interface` or `IPv6Interface`."""
        return self._interface

    @property
    def interface(self) -> IPv4Interface | IPv6Interface:
        """An instance of either `IPv4Interface` or `IPv6Interface`."""
        return self._interface

    @property
    def ip(self) -> IPAddress:
        """IP address of this interface."""
        return IPAddress(self._interface.ip)

    @property
    def network(self) -> 'IPNetwork':
        """Network of this interface."""
        return IPNetwork(self._interface.network)

    @property
    def version(self) -> Literal[4, 6]:
        """IP version (either `4` or `6`)."""
        return self._interface.version

    @property
    def packed(self) -> bytes:
        """Binary representation of the address.

        This is a `bytes` object of `4` bytes length for IPv4, or `16` bytes length for IPv6, with the most significant
        octet first.
        """
        return self._interface.ip.packed

    @property
    def is_ipv4(self) -> bool:
        """`True` if the wrapped interface is an IPv4 interface."""
        return self.version == 4

    @property
    def is_ipv6(self) -> bool:
        """`True` if the wrapped interface is an IPv6 interface."""
        return self.version == 6

    @property
    def hostmask(self) -> IPAddress:
        """Hostmask of this interface."""
        return IPAddress(self._interface.hostmask)

    @property
    def with_prefixlen(self) -> str:
        """String representation of the interface with prefix length."""
        return self._interface.with_prefixlen

    @property
    def with_netmask(self) -> str:
        """String representation of the interface with netmask."""
        return self._interface.with_netmask

    @property
    def with_hostmask(self) -> str:
        """String representation of the interface with hostmask."""
        return self._interface.with_hostmask

    @property
    def is_multicast(self) -> bool:
        """`True` if the interface's network is reserved for multicast use."""
        return self._interface.is_multicast

    @property
    def is_private(self) -> bool:
        """`True` if the interface's network is defined as *not globally reachable*."""
        return self._interface.is_private

    @property
    def is_global(self) -> bool:
        """`True` if the interface's network is defined as *globally reachable*."""
        return self._interface.is_global

    @property
    def is_reserved(self) -> bool:
        """`True` if the interface's network is noted as reserved by the IETF."""
        return self._interface.is_reserved

    @property
    def is_loopback(self) -> bool:
        """`True` if this is a loopback interface's network."""
        return self._interface.is_loopback

    @property
    def is_link_local(self) -> bool:
        """`True` if the interface's network falls within the link-local scope."""
        return self._interface.is_link_local

    @property
    def is_unspecified(self) -> bool:
        """`True` if the interface's network is unspecified."""
        return self._interface.is_unspecified


class IPNetwork(_IPObject):
    """General-purpose IP network wrapper.

    Unifies `ipaddress.IPv4Network` and `ipaddress.IPv6Network` to a single type.
    """

    __slots__ = ('_network',)

    @classmethod
    def __msgspec_decode__(cls, obj: Any) -> Self:
        return cls(obj)

    def __msgspec_encode__(self) -> str:
        return str(self)

    def __init__(
        self,
        address: RawIPAddress | RawNetworkPart | tuple[RawIPAddress] | tuple[RawIPAddress, int],
        *,
        strict: bool = True,
    ) -> None:
        """Initialize an instance of `IPNetwork`.

        Parameters
        ----------
        address : RawIPAddress | RawNetworkPart | tuple[RawIPAddress] | tuple[RawIPAddress, int]
            IP network address. Will be coerced into the appropriate `ipaddress.IPv4Network` or `ipaddress.IPv6Network`
            object instance by the class internally.
        strict : bool, optional
            If `True`, ensure that the host bits are set to zero.

        Raises
        ------
        ipaddress.AddressValueError
            If `address` is not a valid IPv4 or IPv6 network.
        ipaddress.NetmaskValueError
            If the netmask is invalid.
        """
        self._network = ip_network(address, strict=strict)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._network.with_prefixlen!s})'

    def __str__(self) -> str:
        return str(self._network)

    def __hash__(self) -> int:
        return hash(self._network)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, IPNetwork):
            return self._network == other._network
        if isinstance(other, (IPv4Network, IPv6Network)):
            return self._network == other
        if isinstance(other, (str, int, bytes, tuple, IPv4Interface, IPv6Interface)):
            try:
                return self._network == ip_network(other)
            except (ValueError, TypeError):
                return False
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, IPNetwork):
            return self._sort_key() < other._sort_key()
        if isinstance(other, (IPv4Network, IPv6Network)):
            return self._sort_key() < (other.version, int(other.network_address), other.prefixlen)
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, IPNetwork):
            return self._sort_key() <= other._sort_key()
        if isinstance(other, (IPv4Network, IPv6Network)):
            return self._sort_key() <= (other.version, int(other.network_address), other.prefixlen)
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, IPNetwork):
            return self._sort_key() > other._sort_key()
        if isinstance(other, (IPv4Network, IPv6Network)):
            return self._sort_key() > (other.version, int(other.network_address), other.prefixlen)
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, IPNetwork):
            return self._sort_key() >= other._sort_key()
        if isinstance(other, (IPv4Network, IPv6Network)):
            return self._sort_key() >= (other.version, int(other.network_address), other.prefixlen)
        return NotImplemented

    def __contains__(self, other: object) -> bool:
        if isinstance(other, (IPAddress, IPNetwork)):
            other = other.unwrap()
        try:
            return other in self._network
        except (TypeError, ValueError):
            return False

    def __iter__(self) -> Iterator[IPAddress]:
        for ip in self._network:
            yield IPAddress(ip)

    def _sort_key(self) -> tuple[int, int, int]:
        """Return a sort key: (version, network_address_int, prefixlen)."""
        return (self._network.version, int(self._network.network_address), self._network.prefixlen)

    def hosts(self) -> Iterator[IPAddress]:
        """Iterate over the usable hosts within this network.

        Returns
        -------
        Iterator[IPAddress]
            An iterator yielding `IPAddress` objects representing the hosts.
        """
        for ip in self._network.hosts():
            yield IPAddress(ip)

    def subnets(self, prefixlen_diff: int = 1, new_prefix: int | None = None) -> Iterator['IPNetwork']:
        """Generate subnets from this network.

        Parameters
        ----------
        prefixlen_diff : int, optional
            Prefix length difference to be applied when generating subnets.
        new_prefix : int | None, optional
            New prefix length for the subnets.

        Returns
        -------
        Iterator[IPNetwork]
            An iterator yielding `IPNetwork` objects representing the subnets.
        """
        for net in self._network.subnets(prefixlen_diff=prefixlen_diff, new_prefix=new_prefix):
            yield IPNetwork(net)

    def supernet(self, prefixlen_diff: int = 1, new_prefix: int | None = None) -> 'IPNetwork':
        """Return the supernet of this network.

        Parameters
        ----------
        prefixlen_diff : int, optional
            Prefix length difference to be applied when calculating the supernet.
        new_prefix : int | None, optional
            New prefix length for the supernet.

        Returns
        -------
        IPNetwork
            An `IPNetwork` object representing the supernet.
        """
        return IPNetwork(self._network.supernet(prefixlen_diff=prefixlen_diff, new_prefix=new_prefix))

    def address_exclude(self, other: 'IPNetwork | IPv4Network | IPv6Network') -> Iterator['IPNetwork']:
        """Exclude an IP network from this network.

        Parameters
        ----------
        other : IPNetwork | ipaddress.IPv4Network | ipaddress.IPv6Network
            Network to be excluded.

        Returns
        -------
        Iterator[IPNetwork]
            An iterator yielding `IPNetwork` objects representing the remaining networks after exclusion.

        Raises
        ------
        TypeError
            If `other` is not an `IPNetwork`, `ipaddress.IPv4Network`, or `ipaddress.IPv6Network` object instance, or if
            IP versions are mixed.
        """
        candidate = other.unwrap() if isinstance(other, IPNetwork) else other
        if self._network.version == 4 and candidate.version == 4:
            this, that = cast('IPv4Network', self._network), cast('IPv4Network', candidate)
            for net in this.address_exclude(that):
                yield IPNetwork(net)
        elif self._network.version == 6 and candidate.version == 6:
            this, that = cast('IPv6Network', self._network), cast('IPv6Network', candidate)
            for net in this.address_exclude(that):
                yield IPNetwork(net)
        else:
            msg = f'IPv{self.version} and IPv{candidate.version} cannot be mixed'
            raise TypeError(msg)

    def collapse(self, *others: 'IPNetwork | IPv4Network | IPv6Network') -> Iterator['IPNetwork']:
        """Collapse a list of IP networks into the smallest possible list of CIDR networks.

        Parameters
        ----------
        *others : IPNetwork | ipaddress.IPv4Network | ipaddress.IPv6Network
            Additional IP networks to be collapsed with this network.

        Returns
        -------
        Iterator[IPNetwork]
            An iterator yielding `IPNetwork` objects representing the collapsed networks.

        Raises
        ------
        TypeError
            If IP versions are mixed.
        """
        operands = [self._network] + [entry.unwrap() if isinstance(entry, IPNetwork) else entry for entry in others]
        for net in collapse_addresses(cast('Any', operands)):
            yield IPNetwork(net)

    def unwrap(self) -> IPv4Network | IPv6Network:
        """Return the underlying `ipaddress.IPv4Network` or `ipaddress.IPv6Network`."""
        return self._network

    def unwrap_addresses(self) -> Iterator[IPv4Address | IPv6Address]:
        """Return an iterator yielding the underlying `ipaddress.IPv4Address` or `ipaddress.IPv6Address` objects within
        the network.
        """
        yield from self._network

    @property
    def network(self) -> IPv4Network | IPv6Network:
        """An instance of either `ipaddress.IPv4Network` or `ipaddress.IPv6Network`."""
        return self._network

    @property
    def network_address(self) -> IPAddress:
        """Network address of this network."""
        return IPAddress(self._network.network_address)

    @property
    def broadcast_address(self) -> IPAddress:
        """Broadcast address of this network."""
        return IPAddress(self._network.broadcast_address)

    @property
    def netmask(self) -> IPAddress:
        """Netmask of this network."""
        return IPAddress(self._network.netmask)

    @property
    def hostmask(self) -> IPAddress:
        """Hostmask of this network."""
        return IPAddress(self._network.hostmask)

    @property
    def version(self) -> Literal[4, 6]:
        """IP version (either `4` or `6`)."""
        return self._network.version

    @property
    def prefixlen(self) -> int:
        """Prefix length of this network."""
        return self._network.prefixlen

    @property
    def num_addresses(self) -> int:
        """Total number of addresses in this network."""
        return self._network.num_addresses

    @property
    def is_multicast(self) -> bool:
        """`True` if the network is reserved for multicast use."""
        return self._network.is_multicast

    @property
    def is_private(self) -> bool:
        """`True` if the network is defined as *not globally reachable*."""
        return self._network.is_private

    @property
    def is_global(self) -> bool:
        """`True` if the network is defined as *globally reachable*."""
        return self._network.is_global

    @property
    def is_reserved(self) -> bool:
        """`True` if the network is noted as reserved by the IETF."""
        return self._network.is_reserved

    @property
    def is_loopback(self) -> bool:
        """`True` if this is a loopback network."""
        return self._network.is_loopback

    @property
    def is_link_local(self) -> bool:
        """`True` if the network falls within the link-local scope."""
        return self._network.is_link_local

    @property
    def is_unspecified(self) -> bool:
        """`True` if the network is unspecified."""
        return self._network.is_unspecified

    @property
    def with_prefixlen(self) -> str:
        """String representation of the network with prefix length."""
        return self._network.with_prefixlen

    @property
    def with_netmask(self) -> str:
        """String representation of the network with explicit netmask."""
        return self._network.with_netmask

    @property
    def with_hostmask(self) -> str:
        """String representation of the network with explicit hostmask."""
        return self._network.with_hostmask
