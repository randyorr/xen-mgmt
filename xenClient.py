import datetime
import os
import getpass
import json
import socket
import sys
import time
import XenAPI

class Client:

    def __init__(self):
        homedir = os.path.expanduser('~')
        config_file = os.path.join(homedir, '.xen-mgmt')
        if os.path.isfile(config_file):
            f = open(config_file).read()
            settings = json.loads(f)
            user = settings.get('user')
            password = settings.get('password')
            pool = settings.get('pool')
        else:
            user = getpass.getuser()
            password = getpass.getpass()
            print 'select a pool:',
            pool = raw_input()

        self.pool_master = pool
        self.user = user
        self.password = password
        self.auth()

    def auth(self):
        s = socket.socket()
        s.settimeout(0.5)
        port = 443
        try:
            s.connect((self.pool_master,port))
            url = 'https://' + self.pool_master
            try:
                session = XenAPI.Session(url)
                session.login_with_password(self.user, self.password)
            except Exception, e:
                if e.details[0] ==  'HOST_IS_SLAVE':
                    print 'found slave, connecting to... %s' % e.details[1]
                    url = 'https://' + e.details[1]
                    session = XenAPI.Session(url)
                    session.login_with_password(self.user, self.password)
                else:
                    print e
        except(socket.timeout):
            pass
        s.close()
        self.session = session.xenapi

    """
    return all VMs that are not templates or the control domain. name, state, ip, tags only
    """
    def list(self):
        vms = self.session.VM.get_all_records()
        vm_list = []
        for k in vms:
            name = vms[k]['name_label']
            state = vms[k]['power_state']
            vgm = vms[k]['guest_metrics']
            tags = vms[k]['tags']
            if tags == []:
                tags = 'null'
            else:
                tags = ','.join(tags)
            ip = None
            os = None
            if vms[k]['is_a_template'] == False and vms[k]['is_control_domain'] == False:
                try:
                    os = self.session.VM_guest_metrics.get_networks(vgm)
                    if '0/ip' in os.keys():
                        ip = os['0/ip']
                except:
                    pass
                host_ref = vms[k]['resident_on']
                if host_ref == 'OpaqueRef:NULL':
                    host = 'None'
                else:
                    host = self.session.host.get_name_label(host_ref)
                vm_list.append({'name':name, 'state':state, 'tags':tags, 'ip':ip, 'host':host})

        return vm_list

    """
    requires a unique name and a template OpaqueRef. This is based on a template per host scheme. will need new templates per host/network/cpu/memory combination
    TODO: allow templates to be stored on nfs or similar shared storage and select a host to start a VM on. scheduling of resources should also be handled
    """
    def create(self, name, template):
        vm = self.session.VM.clone(template, name)
        try:
            self.session.VM.provision(vm)
            self.session.VM.start(vm, False, False)
        except Exception, e:
            #cleanup - remove disk and vm
            vm_record = self.session.VM.get_record(vm)
            vbds = vm_record['VBDs']
            for v in vbds:
                vbd_record = self.session.VBD.get_record(v)
                if vbd_record['type'] == 'Disk':
                    vdi = vbd_record['VDI']
                    self.session.VDI.destroy(vdi)
            self.session.VM.destroy(vm)
            print 'pick a different xenhost, %s' % e
            return False
        time.sleep(10)
        try:
            record = self.session.VM.get_record(vm)
        except Exception, e:
            print 'failed to provision, check resource availability, %s' % e
            sys.exit(1)
        d = datetime.datetime.now()
        date = d.date().__str__()
        date = 'date:%s' % date
        self.session.VM.set_tags(vm, [date])
        return True

    def delete(self, name):
        vm_ref = self.vm_by_name(name)
        if vm_ref:
            record = self.session.VM.get_record(vm_ref)
            if record['power_state'] == 'Running':
                try:
                    self.session.VM.hard_shutdown(vm_ref)
                except Exception, e:
                    print 'Could not shutdown %s' % vm
            vbds = record['VBDs']
            for v in vbds:
                vbd_record = self.session.VBD.get_record(v)
                if vbd_record['type'] == 'Disk':
                    vdi = vbd_record['VDI']
                    self.session.VDI.destroy(vdi)
            self.session.VM.destroy(vm_ref)
            return True
        else:
            return False


    def vm_by_name(self, name):
        vms = self.session.VM.get_all_records()
        vm = None
        for k in vms:
            name_label = vms[k]['name_label']
            if name == name_label:
                vm = k
        return vm

    """
    return all templates with the cinsay_template tag
    """
    def list_templates(self):
        vms = self.session.VM.get_all_records()
        template_list = {}
        for k in vms:
            if vms[k]['is_a_template']:
                if 'cinsay_template' in vms[k]['tags']:
                    template_list[vms[k]['name_label']] = k
        return template_list

    def get_vm_ip(self,name):
        ip = None
        vm = self.vm_by_name(name)
        record = self.session.VM.get_record(vm)
        guest_metric = record['guest_metrics']
        try:
            os = self.session.VM_guest_metrics.get_networks(guest_metric)
            if '0/ip' in os.keys():
                ip = os['0/ip']
        except:
            pass
        return ip
