import struct
from socket import inet_ntop
from socket import inet_pton
from socket import AF_UNSPEC
from socket import AF_INET
from socket import AF_INET6
from pyroute2.common import AF_MPLS
from pyroute2.common import hexdump
from pyroute2.common import map_namespace
from pyroute2.netlink import nlmsg
from pyroute2.netlink import nla

RTNH_F_DEAD = 1
RTNH_F_PERVASIVE = 2
RTNH_F_ONLINK = 4
RTNH_F_OFFLOAD = 8
RTNH_F_LINKDOWN = 16
(RTNH_F_NAMES, RTNH_F_VALUES) = map_namespace('RTNH_F', globals())

LWTUNNEL_ENCAP_NONE = 0
LWTUNNEL_ENCAP_MPLS = 1
LWTUNNEL_ENCAP_IP = 2
LWTUNNEL_ENCAP_ILA = 3
LWTUNNEL_ENCAP_IP6 = 4
LWTUNNEL_ENCAP_SEG6 = 5
LWTUNNEL_ENCAP_BPF = 6
LWTUNNEL_ENCAP_SEG6_LOCAL = 7


class nlflags(object):

    def encode(self):
        if isinstance(self['flags'], (set, tuple, list)):
            self['flags'] = self.names2flags(self['flags'])
        return super(nlflags, self).encode()

    def flags2names(self, flags=None):
        ret = []
        for flag in RTNH_F_VALUES:
            if (flag & flags) == flag:
                ret.append(RTNH_F_VALUES[flag].lower()[7:])
        return ret

    def names2flags(self, flags=None):
        ret = 0
        for flag in flags or self['flags']:
            ret |= RTNH_F_NAMES['RTNH_F_' + flag.upper()]
        return ret


class rtmsg_base(nlflags):
    '''
    Route message

    C structure::

        struct rtmsg {
            unsigned char rtm_family;   /* Address family of route */
            unsigned char rtm_dst_len;  /* Length of destination */
            unsigned char rtm_src_len;  /* Length of source */
            unsigned char rtm_tos;      /* TOS filter */

            unsigned char rtm_table;    /* Routing table ID */
            unsigned char rtm_protocol; /* Routing protocol; see below */
            unsigned char rtm_scope;    /* See below */
            unsigned char rtm_type;     /* See below */

            unsigned int  rtm_flags;
        };
    '''

    __slots__ = ()

    prefix = 'RTA_'

    fields = (('family', 'B'),
              ('dst_len', 'B'),
              ('src_len', 'B'),
              ('tos', 'B'),
              ('table', 'B'),
              ('proto', 'B'),
              ('scope', 'B'),
              ('type', 'B'),
              ('flags', 'I'))

    nla_map = (('RTA_UNSPEC', 'none'),
               ('RTA_DST', 'target'),
               ('RTA_SRC', 'target'),
               ('RTA_IIF', 'uint32'),
               ('RTA_OIF', 'uint32'),
               ('RTA_GATEWAY', 'target'),
               ('RTA_PRIORITY', 'uint32'),
               ('RTA_PREFSRC', 'target'),
               ('RTA_METRICS', 'metrics'),
               ('RTA_MULTIPATH', '*get_nh'),
               ('RTA_PROTOINFO', 'uint32'),
               ('RTA_FLOW', 'uint32'),
               ('RTA_CACHEINFO', 'cacheinfo'),
               ('RTA_SESSION', 'hex'),
               ('RTA_MP_ALGO', 'hex'),
               ('RTA_TABLE', 'uint32'),
               ('RTA_MARK', 'uint32'),
               ('RTA_MFC_STATS', 'rta_mfc_stats'),
               ('RTA_VIA', 'rtvia'),
               ('RTA_NEWDST', 'target'),
               ('RTA_PREF', 'hex'),
               ('RTA_ENCAP_TYPE', 'uint16'),
               ('RTA_ENCAP', 'encap_info'),
               ('RTA_EXPIRES', 'hex'))

    @staticmethod
    def encap_info(self, *argv, **kwarg):
        encap_type = None

        # Check, if RTA_ENCAP_TYPE is decoded already
        #
        for name, value in self['attrs']:
            if name == 'RTA_ENCAP_TYPE':
                encap_type = value
                break
        else:
            # No RTA_ENCAP_TYPE met, so iterate all the chain.
            # Ugly, but to do otherwise would be too complicated.
            #
            data = kwarg['data']
            offset = kwarg['offset']
            while offset < len(data):
                # Shift offset to the next NLA
                # NLA header:
                #
                # uint16 length
                # uint16 type
                #
                try:
                    offset += struct.unpack('H', data[offset:offset + 2])[0]
                    # 21 == RTA_ENCAP_TYPE
                    # FIXME: should not be hardcoded
                    if struct.unpack('H', data[offset + 2:
                                               offset + 4])[0] == 21:
                        encap_type = struct.unpack('H', data[offset + 4:
                                                             offset + 6])[0]
                        break
                except:
                    # in the case of any decoding error return self.hex
                    break

        # return specific classes
        #
        if encap_type == LWTUNNEL_ENCAP_MPLS:
            return self.mpls_encap_info
        #
        # TODO: add here other lwtunnel types
        #
        # elif encap_type == LWTUNNEL_ENCAP_SEG6:
        #     ...
        #
        return self.hex

    class mpls_encap_info(nla):

        __slots__ = ()

        nla_map = (('MPLS_IPTUNNEL_UNSPEC', 'none'),
                   ('MPLS_IPTUNNEL_DST', 'mpls_target'))

    class rta_mfc_stats(nla):

        __slots__ = ()

        fields = (('mfcs_packets', 'uint64'),
                  ('mfcs_bytes', 'uint64'),
                  ('mfcs_wrong_if', 'uint64'))

    class metrics(nla):

        __slots__ = ()

        prefix = 'RTAX_'
        nla_map = (('RTAX_UNSPEC', 'none'),
                   ('RTAX_LOCK', 'uint32'),
                   ('RTAX_MTU', 'uint32'),
                   ('RTAX_WINDOW', 'uint32'),
                   ('RTAX_RTT', 'uint32'),
                   ('RTAX_RTTVAR', 'uint32'),
                   ('RTAX_SSTHRESH', 'uint32'),
                   ('RTAX_CWND', 'uint32'),
                   ('RTAX_ADVMSS', 'uint32'),
                   ('RTAX_REORDERING', 'uint32'),
                   ('RTAX_HOPLIMIT', 'uint32'),
                   ('RTAX_INITCWND', 'uint32'),
                   ('RTAX_FEATURES', 'uint32'),
                   ('RTAX_RTO_MIN', 'uint32'),
                   ('RTAX_INITRWND', 'uint32'),
                   ('RTAX_QUICKACK', 'uint32'))

    @staticmethod
    def get_nh(self, *argv, **kwarg):
        return nh

    class rtvia(nla):

        __slots__ = ()

        fields = (('value', 's'), )

        def encode(self):
            family = self.get('family', AF_UNSPEC)
            if family in (AF_INET, AF_INET6):
                addr = inet_pton(family, self['addr'])
            else:
                raise TypeError('Family %s not supported for RTA_VIA'
                                % family)
            self['value'] = struct.pack('H', family) + addr
            nla.encode(self)

        def decode(self):
            nla.decode(self)
            family = struct.unpack('H', self['value'][:2])[0]
            addr = self['value'][2:]
            if len(addr):
                if (family == AF_INET and len(addr) == 4) or \
                        (family == AF_INET6 and len(addr) == 16):
                    addr = inet_ntop(family, addr)
                else:
                    addr = hexdump(addr)
            self.value = {'family': family, 'addr': addr}

    class cacheinfo(nla):

        __slots__ = ()

        fields = (('rta_clntref', 'I'),
                  ('rta_lastuse', 'I'),
                  ('rta_expires', 'i'),
                  ('rta_error', 'I'),
                  ('rta_used', 'I'),
                  ('rta_id', 'I'),
                  ('rta_ts', 'I'),
                  ('rta_tsage', 'I'))


class rtmsg(rtmsg_base, nlmsg):

    __slots__ = ()

    def encode(self):
        if self.get('family') == AF_MPLS:
            # force fields
            self['dst_len'] = 20
            self['table'] = 254
            self['type'] = 1
            # assert NLA types
            for n in self.get('attrs', []):
                if n[0] not in ('RTA_OIF',
                                'RTA_DST',
                                'RTA_VIA',
                                'RTA_NEWDST',
                                'RTA_MULTIPATH'):
                    raise TypeError('Incorrect NLA type %s for AF_MPLS' % n[0])
        super(rtmsg_base, self).encode()


class nh(rtmsg_base, nla):

    __slots__ = ()

    is_nla = False
    cell_header = (('length', 'H'), )
    fields = (('flags', 'B'),
              ('hops', 'B'),
              ('oif', 'i'))
