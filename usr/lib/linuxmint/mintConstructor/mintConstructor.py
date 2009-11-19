#!/usr/bin/env python

import sys
import os
import time
import shutil
import locale
import gettext
import re
import commands

try:
     import pygtk
     pygtk.require("2.0")
except Exception, detail:
    print detail
    pass
try:
    import gtk
    import gtk.glade
    import gobject
    import pango
except Exception, detail:
    print detail
    sys.exit(1)


class Reconstructor:

    def __init__(self):
        # vars
        self.gladefile = '/usr/lib/linuxmint/mintConstructor/mintConstructor.glade'
        self.iconFile = '/usr/lib/linuxmint/mintConstructor/icon.svg'

        self.appName = "Live CD Remastering Tool (Ubuntu/Mint)"
        self.codeName = " \"Chartres\" "
        self.devInProgress = False
        self.updateId = "321"
        self.devRevision = "071211"
        self.appVersion = "2.7"
        self.mountDir = '/media/cdrom'
        self.tmpDir = "tmp"
        self.tmpPackageDir = "tmp_packages"
        # type of disc (live/alt)
        self.altBaseTypeStandard = 0
        self.altBaseTypeServer = 1
        self.altBaseTypeDesktop = 2
        self.customDir = ""
        self.createRemasterDir = False
        self.createCustomRoot = False
        self.createInitrdRoot = False
        self.isoFilename = ""
        self.buildLiveCdFilename = ''
        self.setupComplete = False
        self.manualInstall = False
        self.watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
        self.working = None
        self.workingDlg = None
        self.runningDebug = False
        self.interactiveEdit = False
        self.pageLiveSetup = 0
        self.pageLiveCustomize = 1
        self.pageLiveBuild = 2
        self.pageFinish = 3
        self.enableExperimental = False
        self.gnomeBinPath = '/usr/bin/gnome-session'
        self.f = sys.stdout     
        self.treeModel = None
        self.treeView = None      
        
        # time command for timing operations
        self.timeCmd = commands.getoutput('which time') + ' -f \"\nBuild Time: %E  CPU: %P\n\"'

        APPDOMAIN='reconstructor'
        LANGDIR='lang'
        # locale
        locale.setlocale(locale.LC_ALL, '')
        gettext.bindtextdomain(APPDOMAIN, LANGDIR)
        gtk.glade.bindtextdomain(APPDOMAIN, LANGDIR)
        gtk.glade.textdomain(APPDOMAIN)
        gettext.textdomain(APPDOMAIN)
        gettext.install(APPDOMAIN, LANGDIR, unicode=1)

	# i18n for menu item
	menuName = _("Live CD Remastering Tool")
	menuComment = _("Make changes to an ISO or a liveCD")

        # setup glade widget tree
        self.wTree = gtk.glade.XML(self.gladefile, domain='reconstructor')


        # check for user
        if os.getuid() != 0 :
            self.wTree.get_widget("windowMain").hide()

        # create signal dictionary and connect
        dic = { "on_buttonNext_clicked" : self.on_buttonNext_clicked,
            "on_buttonBack_clicked" : self.on_buttonBack_clicked,
            "on_buttonBrowseWorkingDir_clicked" : self.on_buttonBrowseWorkingDir_clicked,
            "on_buttonBrowseIsoFilename_clicked" : self.on_buttonBrowseIsoFilename_clicked,
            "on_checkbuttonBuildIso_toggled" : self.on_checkbuttonBuildIso_toggled,
            "on_buttonBrowseLiveCdFilename_clicked" : self.on_buttonBrowseLiveCdFilename_clicked,
            "on_buttonSoftwareCalculateIsoSize_clicked" : self.on_buttonSoftwareCalculateIsoSize_clicked,
            "on_buttonInteractiveEditLaunch_clicked" : self.on_buttonInteractiveEditLaunch_clicked,
            "on_buttonInteractiveClear_clicked" : self.on_buttonInteractiveClear_clicked,
            "on_buttonCustomizeLaunchTerminal_clicked" : self.on_buttonCustomizeLaunchTerminal_clicked,
            "on_buttonBurnIso_clicked" : self.on_buttonBurnIso_clicked,
            "on_windowMain_delete_event" : gtk.main_quit,
            "on_windowMain_destroy" : self.exitApp }
        self.wTree.signal_autoconnect(dic)     

        # set icons & logo
        self.wTree.get_widget("windowMain").set_icon_from_file(self.iconFile)
        self.wTree.get_widget("imageLogo").set_from_file(self.iconFile)

        # check for existing mount dir
        if os.path.exists(self.mountDir) == False:
            print _('INFO: Creating mount directory...')
            os.makedirs(self.mountDir)

        # set app title
        if self.devInProgress:
            self.wTree.get_widget("windowMain").set_title(self.appName + self.codeName + "  Build " + self.devRevision)
        else:
            self.wTree.get_widget("windowMain").set_title(self.appName)

        # hide back button initially
        self.wTree.get_widget("buttonBack").hide()
        # set default working directory path
	if os.path.exists(os.environ['HOME'] + "/.linuxmint/mintConstructor/currentProject"):
		currentProject = commands.getoutput("cat ~/.linuxmint/mintConstructor/currentProject")
	else:
		currentProject = os.environ['HOME']
	self.wTree.get_widget("entryWorkingDir").set_text(currentProject)	
        # set default iso filenames
        self.wTree.get_widget("entryLiveIsoFilename").set_text(os.path.join(currentProject, "LinuxMint-8-DEV-xxx.iso"))
        # set default descriptions
        cdDesc = _('Linux Mint 8 Helena')
        self.wTree.get_widget("entryLiveCdDescription").set_text(cdDesc)
        # set default cd architectures
        self.wTree.get_widget("comboboxLiveCdArch").set_active(0)
  
    def checkSetup(self):
        setup = False
        if self.createRemasterDir == True:
            setup = True
        elif self.createCustomRoot == True:
            setup = True
        elif self.createInitrdRoot == True:
            setup = True
        else:
            # nothing to be done
            setup = False
        return setup   

    def checkCustomDir(self):
        if self.customDir == "":
            return False
        else:
            if os.path.exists(self.customDir) == False:
                os.makedirs(self.customDir)
            return True

    def setPage(self, pageNum):
        self.wTree.get_widget("notebookWizard").set_current_page(pageNum)

    def setBusyCursor(self):
        self.working = True
        self.wTree.get_widget("windowMain").window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))

    def setDefaultCursor(self):
        self.working = False
        self.wTree.get_widget("windowMain").window.set_cursor(None)

    def showWorking(self):
        self.workingDlg = gtk.Dialog(title="Working")
        self.workingDlg.set_modal(True)
        self.workingDlg.show()

    def hideWorking(self):
        self.workingDlg.hide()

    def checkWorkingDir(self):
        # check for existing directories; if not warn...
        remasterExists = None
        rootExists = None
        initrdExists = None
        if os.path.exists(os.path.join(self.customDir, "remaster")) == False:
            if self.wTree.get_widget("checkbuttonCreateRemaster").get_active() == False:
                remasterExists = False
        if os.path.exists(os.path.join(self.customDir, "root")) == False:
            if self.wTree.get_widget("checkbuttonCreateRoot").get_active() == False:
                rootExists = False
        if os.path.exists(os.path.join(self.customDir, "initrd")) == False:
            if self.wTree.get_widget("checkbuttonCreateInitRd").get_active() == False:
                initrdExists = False
        workingDirOk = True
        if remasterExists == False:
            workingDirOk = False
        if rootExists == False:
            workingDirOk = False
        if initrdExists == False:
            workingDirOk = False
        if workingDirOk == False:
            warnDlg = gtk.Dialog(title=self.appName, parent=None, flags=0, buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK))
            warnDlg.set_icon_from_file(self.iconFile)
            warnDlg.vbox.set_spacing(10)
            labelSpc = gtk.Label(" ")
            warnDlg.vbox.pack_start(labelSpc)
            labelSpc.show()
            lblWarningText = _("  <b>Please fix the errors below before continuing.</b>   ")
            lblRemasterText = _("  There is no remaster directory.  Please select create remaster option.  ")
            lblRootText = _("  There is no root directory.  Please select create root option.  ")
            lblInitrdText = _("  There is no initrd directory.  Please select create initrd option.  ")
            labelWarning = gtk.Label(lblWarningText)
            labelRemaster = gtk.Label(lblRemasterText)
            labelRoot = gtk.Label(lblRootText)
            labelInitrd = gtk.Label(lblInitrdText)

            labelWarning.set_use_markup(True)
            labelRemaster.set_use_markup(True)
            labelRoot.set_use_markup(True)
            labelInitrd.set_use_markup(True)
            warnDlg.vbox.pack_start(labelWarning)
            warnDlg.vbox.pack_start(labelRemaster)
            warnDlg.vbox.pack_start(labelRoot)
            warnDlg.vbox.pack_start(labelInitrd)
            labelWarning.show()

            if remasterExists == False:
                labelRemaster.show()
            if rootExists == False:
                labelRoot.show()
            if initrdExists == False:
                labelInitrd.show()

            #warnDlg.show()
            response = warnDlg.run()
            # HACK: return False no matter what
            if response == gtk.RESPONSE_OK:
                warnDlg.destroy()
            else:
                warnDlg.destroy()

        return workingDirOk

    def checkPage(self, pageNum):
        if self.runningDebug == True:
            print "CheckPage: " + str(pageNum)
            #print " "
        if pageNum == self.pageLiveSetup:
            # setup
            self.saveSetupInfo()
            # reset interactive edit
            self.interactiveEdit = False
            # check for custom dir
            if self.checkCustomDir() == True:
                if self.checkSetup() == True:
                    if self.checkWorkingDir() == True:
                        warnDlg = gtk.Dialog(title=self.appName, parent=None, flags=0, buttons=    (gtk.STOCK_NO, gtk.RESPONSE_CANCEL, gtk.STOCK_YES, gtk.RESPONSE_OK))
                        warnDlg.set_icon_from_file(self.iconFile)
                        warnDlg.vbox.set_spacing(10)
                        labelSpc = gtk.Label(" ")
                        warnDlg.vbox.pack_start(labelSpc)
                        labelSpc.show()
                        lblContinueText = _("  <b>Continue?</b>  ")
                        lblContinueInfo = _("     This may take a few minutes.  Please wait...     ")
                        label = gtk.Label(lblContinueText)
                        lblInfo = gtk.Label(lblContinueInfo)
                        label.set_use_markup(True)
                        warnDlg.vbox.pack_start(label)
                        warnDlg.vbox.pack_start(lblInfo)
                        lblInfo.show()
                        label.show()
                        #warnDlg.show()
                        response = warnDlg.run()
                        if response == gtk.RESPONSE_OK:
                            warnDlg.destroy()
                            self.setBusyCursor()
                            gobject.idle_add(self.setupWorkingDirectory)
                            # calculate iso size
                            gobject.idle_add(self.calculateIsoSize)
                            #self.calculateIsoSize()
                            return True
                        else:
                            warnDlg.destroy()
                            return False
                    else:
                        return False
                else:
                    if self.checkWorkingDir() == True:
                        self.setBusyCursor()
                        # calculate iso size in the background
                        gobject.idle_add(self.calculateIsoSize)
                        #self.calculateIsoSize()
                        return True
                    else:
                        return False
            else:
                warnDlg = gtk.Dialog(title=self.appName, parent=None, flags=0, buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK))
                warnDlg.set_icon_from_file(self.iconFile)
                warnDlg.vbox.set_spacing(10)
                labelSpc = gtk.Label(" ")
                warnDlg.vbox.pack_start(labelSpc)
                labelSpc.show()
                lblWorkingDirText = _("  <b>You must enter a working directory.</b>  ")
                label = gtk.Label(lblWorkingDirText)
                #lblInfo = gtk.Label("     This may take a few minutes.  Please     wait...     ")
                label.set_use_markup(True)
                warnDlg.vbox.pack_start(label)
                #warnDlg.vbox.pack_start(lblInfo)
                #lblInfo.show()
                label.show()
                #warnDlg.show()
                response = warnDlg.run()
                # HACK: return False no matter what
                if response == gtk.RESPONSE_OK:
                    warnDlg.destroy()
                    return False
                else:
                    warnDlg.destroy()
                    return False
        elif pageNum == self.pageLiveCustomize:
	    self.setPage(self.pageLiveBuild)
            self.checkEnableBurnIso()
            return True            

        elif pageNum == self.pageLiveBuild:
            # build
            warnDlg = gtk.Dialog(title=self.appName, parent=None, flags=0, buttons=(gtk.STOCK_NO, gtk.RESPONSE_CANCEL, gtk.STOCK_YES, gtk.RESPONSE_OK))
            warnDlg.set_icon_from_file(self.iconFile)
            warnDlg.vbox.set_spacing(10)
            labelSpc = gtk.Label(" ")
            warnDlg.vbox.pack_start(labelSpc)
            labelSpc.show()
            lblBuildText = _("  <b>Build Live CD?</b>  ")
            lblBuildInfo = _("     This may take a few minutes.  Please wait...     ")
            label = gtk.Label(lblBuildText)
            lblInfo = gtk.Label(lblBuildInfo)
            label.set_use_markup(True)
            warnDlg.vbox.pack_start(label)
            warnDlg.vbox.pack_start(lblInfo)
            lblInfo.show()
            label.show()
            #warnDlg.show()
            response = warnDlg.run()
            if response == gtk.RESPONSE_OK:
                warnDlg.destroy()
                self.setBusyCursor()
                gobject.idle_add(self.build)
                # change Next text to Finish
                self.wTree.get_widget("buttonNext").set_label("Finish")
                return True
            else:
                warnDlg.destroy()
                return False

        elif pageNum == self.pageFinish:
            # finished... exit
            print _("Exiting...")
            gtk.main_quit()
            sys.exit(0)

    def checkEnableBurnIso(self):
        # show burn iso button if nautilus-cd-burner exists
        if commands.getoutput('which nautilus-cd-burner') != '':
            # make sure iso isn't blank
            if os.path.exists(self.wTree.get_widget("entryLiveIsoFilename").get_text()):
                self.wTree.get_widget("buttonBurnIso").show()
            else:
                self.wTree.get_widget("buttonBurnIso").hide()
        else:
            self.wTree.get_widget("buttonBurnIso").hide()


    def exitApp(self):
        gtk.main_quit()
        sys.exit(0)

     
    # launch chroot terminal
    def launchTerminal(self):
        try:
            # setup environment
            # copy dns info
            print _("Copying DNS info...")
            os.popen('cp -f /etc/resolv.conf ' + os.path.join(self.customDir, "root/etc/resolv.conf"))
            # mount /proc
            print _("Mounting /proc filesystem...")
            os.popen('mount --bind /proc \"' + os.path.join(self.customDir, "root/proc") + '\"')
            # copy apt.conf
            #print _("Copying apt.conf configuration...")
            #os.popen('cp -f /etc/apt/apt.conf ' + os.path.join(self.customDir, "root/etc/apt/apt.conf"))
            # copy wgetrc
            print _("Copying wgetrc configuration...")
            # backup
            os.popen('mv -f \"' + os.path.join(self.customDir, "root/etc/wgetrc") + '\" \"' + os.path.join(self.customDir, "root/etc/wgetrc.orig") + '\"')
            os.popen('cp -f /etc/wgetrc ' + os.path.join(self.customDir, "root/etc/wgetrc"))
            # HACK: create temporary script for chrooting
            scr = '#!/bin/sh\n#\n#\t(c) reconstructor, 2006\n#\nchroot ' + os.path.join(self.customDir, "root/") + '\n'
            f=open('/tmp/reconstructor-terminal.sh', 'w')
            f.write(scr)
            f.close()
            os.popen('chmod a+x ' + os.path.join(self.customDir, "/tmp/reconstructor-terminal.sh"))
            # TODO: replace default terminal title with "Reconstructor Terminal"
            # use gnome-terminal if available -- more features
	    #if commands.getoutput('which gnome-terminal') != '':
	    #	print _('Launching Gnome-Terminal for advanced customization...')
	    #	os.popen('export HOME=/root ; gnome-terminal --hide-menubar -t \"Reconstructor Terminal\" -e \"/tmp/reconstructor-terminal.sh\"')
	    if commands.getoutput('which xterm') != '':
		print _('Launching Xterm for advanced customization...')
	    	# use xterm if gnome-terminal isn't available
	    	os.popen('export HOME=/root ; xterm -bg black -fg white -rightbar -title \"Reconstructor Terminal\" -e /tmp/reconstructor-terminal.sh')
 	    else:
	    	print _('Error: no valid terminal found')
	    	gtk.main_quit()
	    	sys.exit(1)

            # restore wgetrc
            print _("Restoring wgetrc configuration...")
            os.popen('mv -f \"' + os.path.join(self.customDir, "root/etc/wgetrc.orig") + '\" \"' + os.path.join(self.customDir, "root/etc/wgetrc") + '\"')
            # remove apt.conf
            #print _("Removing apt.conf configuration...")
            #os.popen('rm -Rf \"' + os.path.join(self.customDir, "root/etc/apt/apt.conf") + '\"')
            # remove dns info
            print _("Removing DNS info...")
            os.popen('rm -Rf \"' + os.path.join(self.customDir, "root/etc/resolv.conf") + '\"')
            # umount /proc
            print _("Umounting /proc...")
            os.popen('umount \"' + os.path.join(self.customDir, "root/proc/") + '\"')
            # remove temp script
            os.popen('rm -Rf /tmp/reconstructor-terminal.sh')

        except Exception, detail:
            # restore settings
            # restore wgetrc
            print _("Restoring wgetrc configuration...")
            os.popen('mv -f \"' + os.path.join(self.customDir, "root/etc/wgetrc.orig") + '\" \"' + os.path.join(self.customDir, "root/etc/wgetrc") + '\"')
            # remove apt.conf
            #print _("Removing apt.conf configuration...")
            #os.popen('rm -Rf \"' + os.path.join(self.customDir, "root/etc/apt/apt.conf") + '\"')
            # remove dns info
            print _("Removing DNS info...")
            os.popen('rm -Rf \"' + os.path.join(self.customDir, "root/etc/resolv.conf") + '\"')
            # umount /proc
            print _("Umounting /proc...")
            os.popen('umount \"' + os.path.join(self.customDir, "root/proc/") + '\"')
            # remove temp script
            os.popen('rm -Rf /tmp/reconstructor-terminal.sh')

            errText = _('Error launching terminal: ')
            print errText, detail
            pass

        return

    # Burns ISO
    def burnIso(self):
        try:
            if commands.getoutput('which nautilus-cd-burner') != '':
                print _('Burning ISO...')
                os.popen('nautilus-cd-burner --source-iso=\"' + self.buildLiveCdFilename + '\"')
            else:
                print _('Error: nautilus-cd-burner is needed for burning iso files... ')

        except Exception, detail:
            errText = _('Error burning ISO: ')
            print errText, detail
            pass   


    def calculateIsoSize(self):
        try:
            # reset current size
            self.wTree.get_widget("labelSoftwareIsoSize").set_text("")
            totalSize = None
            remasterSize = 0
            rootSize = 0
            squashSize = 0
            print _('Calculating Live ISO Size...')
            # regex for extracting size
            r = re.compile('(\d+)\s', re.IGNORECASE)
            # get size of remaster dir - use du -s (it's faster)
            remaster = commands.getoutput('du -s ' + os.path.join(self.customDir, "remaster/"))
            mRemaster = r.match(remaster)
            remasterSize = int(mRemaster.group(1))

            # subtract squashfs root
            if os.path.exists(os.path.join(self.customDir, "remaster/casper/filesystem.squashfs")):
                squash = commands.getoutput('du -s ' + os.path.join(self.customDir, "remaster/casper/filesystem.squashfs"))
                mSquash = r.match(squash)
                squashSize = int(mSquash.group(1))
	    print "OK"
            remasterSize -= squashSize
            # get size of root dir
            root = commands.getoutput('du -s ' + os.path.join(self.customDir, "root/"))
            mRoot = r.match(root)
            rootSize = int(mRoot.group(1))

            # divide root size to simulate squash compression
            self.wTree.get_widget("labelSoftwareIsoSize").set_text( '~ ' + str(int(round((remasterSize + (rootSize/3.185))/1024))) + ' MB')
            self.setDefaultCursor()
            # set page here - since this is run on a background thread,
            # the next page will show too quickly if set in self.checkPage()
            self.setPage(self.pageLiveCustomize)
        except Exception, detail:
            errText = _("Error calculating estimated iso size: ")
            print errText, detail
            pass    

    def startInteractiveEdit(self):
        print _('Beginning Interactive Editing...')
        # set interactive edit tag
        self.interactiveEdit = True
        # check for template user home directory; create if necessary
        #print ('useradd -d /home/reconstructor -m -s /bin/bash -p ' + str(os.urandom(8)))
        if os.path.exists('/home/reconstructor') == False:
            # create user with random password
            password = 'r0714'
            os.popen('useradd -d /home/reconstructor -s /bin/bash -p ' + password +' reconstructor')
            # create home dir
            os.popen('mkdir -p /home/reconstructor')
            # change owner of home
            os.popen('chown -R reconstructor /home/reconstructor')
        # launch Xnest in background
        try:
            print _('Starting Xnest in the background...')
            os.popen('Xnest :1 -ac -once & 1>&2 2>/dev/null')
        except Exception, detail:
            errXnest = _("Error starting Xnest: ")
            print errXnest, detail
            return
        # try to start gnome-session with template user
        try:
            print _('Starting Gnome-Session....')
            #os.popen('chroot \"' + os.path.join(self.customDir, "root/") + '\" ' + 'su -c \"export DISPLAY=localhost:1 ; gnome-session\" 1>&2 2>/dev/null\"')
            #os.popen("chroot /home/ehazlett/reconstructor/root \"/tmp/test.sh\"")
            os.popen('su reconstructor -c \"export DISPLAY=:1 ; gnome-session\" 1>&2 2>/dev/null')
        except Exception, detail:
            errGnome = _("Error starting Gnome-Session: ")
            print errGnome, detail
            return

    def clearInteractiveSettings(self):
        try:
            print _('Clearing Interactive Settings...')
            print _('Removing \'reconstructor\' user...')
            os.popen('userdel reconstructor')
            print _('Removing \'reconstructor\' home directory...')
            os.popen('rm -Rf /home/reconstructor')
            self.setDefaultCursor()
        except Exception, detail:
            self.setDefaultCursor()
            errText = _('Error clearing interactive settings: ')
            print errText, detail
            pass  

    def on_buttonBack_clicked(self, widget):
        # HACK: back pressed so change buttonNext text
        self.wTree.get_widget("buttonNext").set_label("Next")
        # HACK: get_current_page() returns after the click, so check for 1 page ahead
        # check for first step; disable if needed
        if self.wTree.get_widget("notebookWizard").get_current_page() == 0:
            self.wTree.get_widget("buttonBack").hide()
        # check for disc type and move to proper locations
        elif self.wTree.get_widget("notebookWizard").get_current_page() == self.pageFinish:           
            self.setPage(self.pageLiveBuild)            
        else:
            self.wTree.get_widget("notebookWizard").prev_page()

    def on_buttonNext_clicked(self, widget):
        page = self.wTree.get_widget("notebookWizard").get_current_page()
        # HACK: show back button
        self.wTree.get_widget("buttonBack").show()
        #if (self.checkPage(page)):
        #    self.wTree.get_widget("notebookWizard").next_page()
        self.checkPage(page)

    def on_buttonBrowseWorkingDir_clicked(self, widget):
        dlgTitle = _('Select Working Directory')
        workingDlg = gtk.FileChooserDialog(title=dlgTitle, parent=self.wTree.get_widget("windowMain"), action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK), backend=None)
        workingDlg.set_uri(os.environ['HOME'] + '/reconstructor')
        response = workingDlg.run()
        if response == gtk.RESPONSE_OK :
            filename = workingDlg.get_current_folder()
            self.wTree.get_widget("entryWorkingDir").set_text(workingDlg.get_filename())
            workingDlg.hide()
        elif response == gtk.RESPONSE_CANCEL :
            workingDlg.destroy()

    def on_buttonBrowseIsoFilename_clicked(self, widget):
        # filter only iso files
        isoFilter = gtk.FileFilter()
        isoFilter.set_name("ISO Files (.iso)")
        isoFilter.add_pattern("*.iso")
        # create dialog
        dlgTitle = _('Select Live CD ISO')
        isoDlg = gtk.FileChooserDialog(title=dlgTitle, parent=self.wTree.get_widget("windowMain"), action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK), backend=None)
        isoDlg.add_filter(isoFilter)
        isoDlg.set_current_folder(os.environ['HOME'])
        response = isoDlg.run()
        if response == gtk.RESPONSE_OK :
            self.wTree.get_widget("entryIsoFilename").set_text(isoDlg.get_filename())
            isoDlg.hide()
        elif response == gtk.RESPONSE_CANCEL :
            isoDlg.destroy()

    def on_buttonBrowseLiveCdFilename_clicked(self, widget):
        # filter only iso files
        isoFilter = gtk.FileFilter()
        isoFilter.set_name("ISO Files")
        isoFilter.add_pattern("*.iso")
        # create dialog
        dlgTitle = _('Select Live CD Filename')
        isoDlg = gtk.FileChooserDialog(title=dlgTitle, parent=self.wTree.get_widget("windowMain"), action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK), backend=None)
        isoDlg.add_filter(isoFilter)
        isoDlg.set_select_multiple(False)
        isoDlg.set_current_folder(os.environ['HOME'])
        response = isoDlg.run()
        if response == gtk.RESPONSE_OK :
            self.wTree.get_widget("entryLiveIsoFilename").set_text(isoDlg.get_filename())
            isoDlg.hide()
        elif response == gtk.RESPONSE_CANCEL :
            isoDlg.destroy()  

    def on_checkbuttonBuildIso_toggled(self, widget):
        if self.wTree.get_widget("checkbuttonBuildIso").get_active() == True:
            # show filename, description, etc. entry
            self.wTree.get_widget("tableLiveCd").show()
        else:
            # hide filename entry
            self.wTree.get_widget("tableLiveCd").hide()   

    def on_buttonSoftwareCalculateIsoSize_clicked(self, widget):
        self.setBusyCursor()
        gobject.idle_add(self.calculateIsoSize)

    def on_buttonInteractiveEditLaunch_clicked(self, widget):
        self.startInteractiveEdit()

    def on_buttonInteractiveClear_clicked(self, widget):
        warnDlg = gtk.Dialog(title=self.appName, parent=None, flags=0, buttons=(gtk.STOCK_NO, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))
        warnDlg.set_icon_from_file(self.iconFile)
        warnDlg.vbox.set_spacing(10)
        labelSpc = gtk.Label(" ")
        warnDlg.vbox.pack_start(labelSpc)
        labelSpc.show()
        lblContinueText = _("  <b>Delete?</b>  ")
        label = gtk.Label(lblContinueText)
        label.set_use_markup(True)
        warnDlg.vbox.pack_start(label)
        label.show()
        #warnDlg.show()
        response = warnDlg.run()
        if response == gtk.RESPONSE_OK:
            warnDlg.destroy()
            self.setBusyCursor()
            # clear settings
            gobject.idle_add(self.clearInteractiveSettings)
        else:
            warnDlg.destroy()      

    def on_buttonCustomizeLaunchTerminal_clicked(self, widget):
        self.launchTerminal()

    def on_buttonBurnIso_clicked(self, widget):
        self.burnIso()       
 
    def saveSetupInfo(self):
        # do setup - check and create dirs as needed
        print _("INFO: Saving working directory information...")
        self.customDir = self.wTree.get_widget("entryWorkingDir").get_text()
	os.system("mkdir -p ~/.linuxmint/mintConstructor")
	os.system("echo \"" + self.customDir + "\" > ~/.linuxmint/mintConstructor/currentProject")
        self.createRemasterDir = self.wTree.get_widget("checkbuttonCreateRemaster").get_active()
        self.createCustomRoot = self.wTree.get_widget("checkbuttonCreateRoot").get_active()
        self.createInitrdRoot = self.wTree.get_widget("checkbuttonCreateInitRd").get_active()
        self.isoFilename = self.wTree.get_widget("entryIsoFilename").get_text()
        # debug
        print "Custom Directory: " + str(self.customDir)
        print "Create Remaster Directory: " + str(self.createRemasterDir)
        print "Create Custom Root: " + str(self.createCustomRoot)
        print "Create Initrd Root: " + str(self.createInitrdRoot)
        print "ISO Filename: " + str(self.isoFilename)

# ---------- Setup ---------- #
    def setupWorkingDirectory(self):
        print _("INFO: Setting up working directory...")
        # remaster dir
        if self.createRemasterDir == True:
            # check for existing directories and remove if necessary
            #if os.path.exists(os.path.join(self.customDir, "remaster")):
            #    print _("INFO: Removing existing Remaster directory...")
            #    os.popen('rm -Rf \"' + os.path.join(self.customDir, "remaster/") + '\"')
            if os.path.exists(os.path.join(self.customDir, "remaster")) == False:
                print "INFO: Creating Remaster directory..."
                os.makedirs(os.path.join(self.customDir, "remaster"))
            # check for iso
            if self.isoFilename == "":
                mntDlg = gtk.Dialog(title=self.appName, parent=None, flags=0, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))
                mntDlg.set_icon_from_file(self.iconFile)
                mntDlg.vbox.set_spacing(10)
                labelSpc = gtk.Label(" ")
                mntDlg.vbox.pack_start(labelSpc)
                labelSpc.show()
                lblText = _("  <b>Please insert the Live CD and click OK</b>  ")
                label = gtk.Label(lblText)
                label.set_use_markup(True)
                mntDlg.vbox.pack_start(label)
                label.show()
                #warnDlg.show()
                response = mntDlg.run()
                if response == gtk.RESPONSE_OK:
                    print _("Using Live CD for remastering...")
                    mntDlg.destroy()
                    os.popen("mount " + self.mountDir)
                else:
                    mntDlg.destroy()
                    self.setDefaultCursor()
                    return
            else:
                print _("Using ISO for remastering...")
                os.popen('mount -o loop \"' + self.isoFilename + '\" ' + self.mountDir)

            print _("Copying files...")

            # copy remaster files
            os.popen('rsync -at --del ' + self.mountDir + '/ \"' + os.path.join(self.customDir, "remaster") + '\"')
            print _("Finished copying files...")

            # unmount iso/cd-rom
            os.popen("umount " + self.mountDir)
        # custom root dir
        if self.createCustomRoot == True:
            #if os.path.exists(os.path.join(self.customDir, "root")):
            #    print _("INFO: Removing existing Custom Root directory...")

            #    os.popen('rm -Rf \"' + os.path.join(self.customDir, "root/") + '\"')
            if os.path.exists(os.path.join(self.customDir, "root")) == False:
                print _("INFO: Creating Custom Root directory...")
                os.makedirs(os.path.join(self.customDir, "root"))
            # check for existing directories and remove if necessary
            if os.path.exists(os.path.join(self.customDir, "tmpsquash")):
                print _("INFO: Removing existing tmpsquash directory...")

                os.popen('rm -Rf \"' + os.path.join(self.customDir, "tmpsquash") + '\"')

            # extract squashfs into custom root
            # check for iso
            if self.isoFilename == "":
                mntDlg = gtk.Dialog(title=self.appName, parent=None, flags=0, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))
                mntDlg.set_icon_from_file(self.iconFile)
                mntDlg.vbox.set_spacing(10)
                labelSpc = gtk.Label(" ")
                mntDlg.vbox.pack_start(labelSpc)
                labelSpc.show()
                lblText = _("  <b>Please insert the Live CD and click OK</b>  ")
                label = gtk.Label(lblText)
                label.set_use_markup(True)
                mntDlg.vbox.pack_start(label)
                label.show()
                response = mntDlg.run()
                if response == gtk.RESPONSE_OK:
                    print _("Using Live CD for squashfs root...")
                    mntDlg.destroy()
                    os.popen("mount " + self.mountDir)
                else:
                    mntDlg.destroy()
                    self.setDefaultCursor()
                    return
            else:
                print _("Using ISO for squashfs root...")
                os.popen('mount -o loop \"' + self.isoFilename + '\" ' + self.mountDir)

            # copy remaster files
            os.mkdir(os.path.join(self.customDir, "tmpsquash"))
            # mount squashfs root
            print _("Mounting squashfs...")
            os.popen('mount -t squashfs -o loop ' + self.mountDir + '/casper/filesystem.squashfs \"' + os.path.join(self.customDir, "tmpsquash") + '\"')
            print _("Extracting squashfs root...")

            # copy squashfs root
            os.popen('rsync -at --del \"' + os.path.join(self.customDir, "tmpsquash") + '\"/ \"' + os.path.join(self.customDir, "root/") + '\"')

            # umount tmpsquashfs
            print _("Unmounting tmpsquash...")
            os.popen('umount --force \"' + os.path.join(self.customDir, "tmpsquash") + '\"')
            # umount cdrom
            print _("Unmounting cdrom...")
            os.popen("umount --force " + self.mountDir)
            # remove tmpsquash
            print _("Removing tmpsquash...")
            os.popen('rm -Rf \"' + os.path.join(self.customDir, "tmpsquash") + '\"')
            # set proper permissions - MUST DO WITH UBUNTU
            print _("Setting proper permissions...")
            os.popen('chmod 6755 \"' + os.path.join(self.customDir, "root/usr/bin/sudo") + '\"')
            os.popen('chmod 0440 \"' + os.path.join(self.customDir, "root/etc/sudoers") + '\"')
            print _("Finished extracting squashfs root...")
	    if os.path.exists("/usr/bin/aplay"):
	        os.system("/usr/bin/aplay /usr/lib/linuxmint/mintConstructor/done.wav")

        # initrd dir
        if self.createInitrdRoot == True:
            if os.path.exists(os.path.join(self.customDir, "initrd")):
                print _("INFO: Removing existing Initrd directory...")
                os.popen('rm -Rf \"' + os.path.join(self.customDir, "initrd/") + '\"')
            print _("INFO: Creating Initrd directory...")
            os.makedirs(os.path.join(self.customDir, "initrd"))
            # check for iso
            if self.isoFilename == "":
                mntDlg = gtk.Dialog(title=self.appName, parent=None, flags=0, buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))
                mntDlg.set_icon_from_file(self.iconFile)
                mntDlg.vbox.set_spacing(10)
                labelSpc = gtk.Label(" ")
                mntDlg.vbox.pack_start(labelSpc)
                labelSpc.show()
                lblText = _("  <b>Please insert the Live CD and click OK</b>  ")
                label = gtk.Label(lblText)
                label.set_use_markup(True)
                mntDlg.vbox.pack_start(label)
                label.show()
                response = mntDlg.run()
                if response == gtk.RESPONSE_OK:
                    print _("Using Live CD for initrd...")
                    mntDlg.destroy()
                    os.popen("mount " + self.mountDir)
                else:
                    mntDlg.destroy()
                    self.setDefaultCursor()
                    return
            else:
                print _("Using ISO for initrd...")
                os.popen('mount -o loop \"' + self.isoFilename + '\" ' + self.mountDir)

            # extract initrd
            print _("Extracting Initial Ram Disk (initrd)...")
	    if os.path.exists(self.mountDir + '/casper/initrd.lz'):
	        os.popen('cd \"' + os.path.join(self.customDir, "initrd/") + '\"; lzma -dc -S .lz ' + self.mountDir + '/casper/initrd.lz | cpio -id')
            elif os.path.exists(self.mountDir + '/casper/initrd.gz'):
                os.popen('cd \"' + os.path.join(self.customDir, "initrd/") + '\"; cat ' + self.mountDir + '/casper/initrd.gz | gzip -d | cpio -i')
            # umount cdrom
            os.popen("umount " + self.mountDir)

        # load comboboxes for customization
        #self.hideWorking()
        self.setDefaultCursor()
        self.setPage(self.pageLiveCustomize)
        print _("Finished setting up working directory...")
        print " "
        return False

# ---------- Build ---------- #
    def build(self):
        # check for custom mksquashfs (for multi-threading, new features, etc.)
        mksquashfs = ''
        if commands.getoutput('echo $MKSQUASHFS') != '':
            mksquashfs = commands.getoutput('echo $MKSQUASHFS')
            print 'Using alternative mksquashfs: ' + ' Version: ' + commands.getoutput(mksquashfs + ' -version')
        # setup build vars
        self.buildInitrd = self.wTree.get_widget("checkbuttonBuildInitrd").get_active()
        self.buildSquashRoot = self.wTree.get_widget("checkbuttonBuildSquashRoot").get_active()
        self.buildIso = self.wTree.get_widget("checkbuttonBuildIso").get_active()
        self.buildLiveCdFilename = self.wTree.get_widget("entryLiveIsoFilename").get_text()
        self.LiveCdDescription = "Linux Mint x yyy"
        self.LiveCdArch = self.wTree.get_widget("comboboxLiveCdArch").get_active_text()
        self.hfsMap = os.getcwd() + "/lib/hfs.map"

        print " "
        print _("INFO: Starting Build...")
        print " "
        # build initrd
        if self.buildInitrd == True:
            # create initrd
            if os.path.exists(os.path.join(self.customDir, "initrd")):
                print _("Creating Initrd...")
                #os.popen('cd \"' + os.path.join(self.customDir, "initrd/") + '\"; find | cpio -H newc -o | gzip > ../initrd.gz' + '; mv -f ../initrd.gz \"' + os.path.join(self.customDir, "remaster/casper/initrd.gz") + '\"')
                os.popen('cd \"' + os.path.join(self.customDir, "initrd/") + '\"; find | cpio -H newc -o | lzma -7 > ../initrd.lz' + '; mv -f ../initrd.lz \"' + os.path.join(self.customDir, "remaster/casper/initrd.lz") + '\"')

        # build squash root
        if self.buildSquashRoot == True:
            # create squashfs root
            if os.path.exists(os.path.join(self.customDir, "root")):
                print _("Creating SquashFS root...")
                print _("Updating File lists...")
                q = ' dpkg-query -W --showformat=\'${Package} ${Version}\n\' '
                os.popen('chroot \"' + os.path.join(self.customDir, "root/") + '\"' + q + ' > \"' + os.path.join(self.customDir, "remaster/casper/filesystem.manifest") + '\"' )
                os.popen('cp -f \"' + os.path.join(self.customDir, "remaster/casper/filesystem.manifest") + '\" \"' + os.path.join(self.customDir, "remaster/casper/filesystem.manifest-desktop") + '\"')
                # check for existing squashfs root
                if os.path.exists(os.path.join(self.customDir, "remaster/casper/filesystem.squashfs")):
                    print _("Removing existing SquashFS root...")
                    os.popen('rm -Rf \"' + os.path.join(self.customDir, "remaster/casper/filesystem.squashfs") + '\"')
                print _("Building SquashFS root...")
                # check for alternate mksquashfs
                if mksquashfs == '':
                    os.popen(self.timeCmd + ' mksquashfs \"' + os.path.join(self.customDir, "root/") + '\"' + ' \"' + os.path.join(self.customDir, "remaster/casper/filesystem.squashfs") + '\"')
                else:
                    os.popen(self.timeCmd + ' ' + mksquashfs + ' \"' + os.path.join(self.customDir, "root/") + '\"' + ' \"' + os.path.join(self.customDir, "remaster/casper/filesystem.squashfs") + '\"')

        # build iso
        if self.buildIso == True:
            # create iso
            if os.path.exists(os.path.join(self.customDir, "remaster")):
                print _("Creating ISO...")
                # add disc id
                #os.popen('echo \"Built by Reconstructor ' + self.appVersion + ' - Rev ' + self.updateId + ' (c) Reconstructor Team, 2006 - http://reconstructor.aperantis.com\" > \"' + os.path.join(self.customDir, "remaster/.disc_id") + '\"')
		# update manifest files
		os.system("/usr/lib/linuxmint/mintConstructor/updateManifest.sh " + self.customDir)
                # update md5
                print _("Updating md5 sums...")
                os.system('rm ' + os.path.join(self.customDir, "remaster/") + ' md5sum.txt')
                os.popen('cd \"' + os.path.join(self.customDir, "remaster/") + '\"; ' + 'find . -type f -print0 | xargs -0 md5sum > md5sum.txt')
		#Remove md5sum.txt from md5sum.txt
		os.system("sed -e '/md5sum.txt/d' " + os.path.join(self.customDir, "remaster/") + "md5sum.txt > " + os.path.join(self.customDir, "remaster/") + "md5sum.new")
		os.system("mv " + os.path.join(self.customDir, "remaster/") + "md5sum.new " + os.path.join(self.customDir, "remaster/") + "md5sum.txt")
		#Remove boot.cat from md5sum.txt
		os.system("sed -e '/boot.cat/d' " + os.path.join(self.customDir, "remaster/") + "md5sum.txt > " + os.path.join(self.customDir, "remaster/") + "md5sum.new")
		os.system("mv " + os.path.join(self.customDir, "remaster/") + "md5sum.new " + os.path.join(self.customDir, "remaster/") + "md5sum.txt")
                # remove existing iso
                if os.path.exists(self.buildLiveCdFilename):
                    print _("Removing existing ISO...")
                    os.popen('rm -Rf \"' + self.buildLiveCdFilename + '\"')
                # build
                # check for description - replace if necessary
                if self.wTree.get_widget("entryLiveCdDescription").get_text() != "":
                    self.LiveCdDescription = self.wTree.get_widget("entryLiveCdDescription").get_text()

                # build iso according to architecture
                #if self.LiveCdArch == "x86":
                print _("Building x86 ISO...")
                os.popen(self.timeCmd + ' mkisofs -o \"' + self.buildLiveCdFilename + '\" -b \"isolinux/isolinux.bin\" -c \"isolinux/boot.cat\" -no-emul-boot -boot-load-size 4 -boot-info-table -V \"' + self.LiveCdDescription + '\" -cache-inodes -r -J -l \"' + os.path.join(self.customDir, "remaster") + '\"')
                #elif self.LiveCdArch == "PowerPC":
                #    print _("Building PowerPC ISO...")
                #    os.popen(self.timeCmd + ' mkisofs  -r -V \"' + self.LiveCdDescription + '\" --netatalk -hfs -probe -map \"' + self.hfsMap + '\" -chrp-boot -iso-level 2 -part -no-desktop -hfs-bless ' + '\"' + os.path.join(self.customDir, "remaster/install") + '\" -o \"' + self.buildLiveCdFilename + '\" \"' + os.path.join(self.customDir, "remaster") + '\"')
                #elif self.LiveCdArch == "x86_64":
                 #   print _("Building x86_64 ISO...")
                  #  os.popen(self.timeCmd + ' mkisofs -r -o \"' + self.buildLiveCdFilename + '\" -b \"isolinux/isolinux.bin\" -c \"isolinux/boot.cat\" -no-emul-boot -V \"' + self.LiveCdDescription + '\" -J -l \"' + os.path.join(self.customDir, "remaster") + '\"')

        self.setDefaultCursor()
        self.setPage(self.pageFinish)
        # print status message
        statusMsgFinish = _('     <b>Finished.</b>     ')
        statusMsgISO = _('      <b>Finished.</b> ISO located at: ')
        if os.path.exists(self.buildLiveCdFilename):
            print "ISO Located: " + self.buildLiveCdFilename
            self.wTree.get_widget("labelBuildComplete").set_text(statusMsgISO + self.buildLiveCdFilename + '     ')
            self.wTree.get_widget("labelBuildComplete").set_use_markup(True)
        else:
            self.wTree.get_widget("labelBuildComplete").set_text(statusMsgFinish)
            self.wTree.get_widget("labelBuildComplete").set_use_markup(True)
        # enable/disable iso burn
        self.checkEnableBurnIso()

        print "Build Complete..."
	if os.path.exists("/usr/bin/aplay"):
		os.system("/usr/bin/aplay /usr/lib/linuxmint/mintConstructor/done.wav")

# ---------- MAIN ----------

if __name__ == "__main__":
    APPDOMAIN='reconstructor'
    LANGDIR='lang'
    # locale
    locale.setlocale(locale.LC_ALL, '')
    gettext.bindtextdomain(APPDOMAIN, LANGDIR)
    gtk.glade.bindtextdomain(APPDOMAIN, LANGDIR)
    gtk.glade.textdomain(APPDOMAIN)
    gettext.textdomain(APPDOMAIN)
    gettext.install(APPDOMAIN, LANGDIR, unicode=1)

    # check credentials
    if os.getuid() != 0 :
        ## show non-root privledge error
        warnDlg = gtk.Dialog(title="mintConstructor", parent=None, flags=0, buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK))
        warnDlg.set_icon_from_file('/usr/lib/linuxmint/mintConstructor/icon.svg')
        warnDlg.vbox.set_spacing(10)
        labelSpc = gtk.Label(" ")
        warnDlg.vbox.pack_start(labelSpc)
        labelSpc.show()
        warnText = _("  <b>You must run with root privileges.</b>")
        infoText = _("Insufficient permissions")
        label = gtk.Label(warnText)
        lblInfo = gtk.Label(infoText)
        label.set_use_markup(True)
        lblInfo.set_use_markup(True)
        warnDlg.vbox.pack_start(label)
        warnDlg.vbox.pack_start(lblInfo)
        label.show()
        lblInfo.show()
        response = warnDlg.run()
        if response == gtk.RESPONSE_OK :
            warnDlg.destroy()
            #gtk.main_quit()
            sys.exit(0)
        # use gksu to open -- HIDES TERMINAL
        #os.popen('gksu ' + os.getcwd() + '/reconstructor.py')
        #gtk.main_quit()
        #sys.exit(0)
    else :
        rec = Reconstructor()
        # run gui
        gtk.main()
