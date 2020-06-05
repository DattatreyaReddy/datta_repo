import datetime, json, re, time
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler,  PicklePersistence
import logging
from python.dbCreate import teleDb
#from dbCreate import teleDb
tkn = open('data/stdtkn.txt').read()
bot = telegram.Bot(token=tkn)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
END = ConversationHandler.END
logger = logging.getLogger(__name__)
class stdchat:
    '''
        Class for telegram chat bot - CR_Alt (STUDENT VER)
    '''
    #Constants to use in dict as keys for Conversation Handler
    Setup_MH, Rollupd_MH, Menu_opt_MH, Day_MH, Set_Atd_MH, Set_Atdpa_MH= range(6)
    updusr = False

    #init function

    def __init__(self,db):
        '''
            Init  self.updater,Jobqueue,
            Adds message handlers, nested conversation handlers,
            starts polling
        '''
        # self.Setup_CH,self.Timetable_CH,self.Daily_Timetable_CH,self.Get_Attendance_CH,self.Set_Attendance = range(5)
        self.db = db
        self.daylst = ['Monday','Tuesday','Wednesday','Thursday','Friday',"Go to Menu"]
        pp = PicklePersistence(filename='data/Stdcraltbot')
        self.updater = Updater(token=tkn,persistence=pp,use_context=True)
        dp =  self.updater.dispatcher
        j =  self.updater.job_queue
        j.run_daily(self.callback_daily,datetime.time(18,47,0,0),(0,1,2,3,4),context=telegram.ext.CallbackContext)
        
        # Daily timetable conv

        Daily_tt_cov = ConversationHandler(
                    entry_points=[MessageHandler((Filters.text("Daily Timetable")),self.daykb)],
                    states= {
                        self.Day_MH : [MessageHandler((Filters.text & (Filters.regex(r".*DAY") | Filters.regex(r".*day") ) 
                                                            & (~Filters.command)),self.stddtt),
                                            MessageHandler((Filters.text('Go to Menu')),self.menu)]
                    },
                    allow_reentry= True,
                     map_to_parent={self.Menu_opt_MH : self.Menu_opt_MH,
                                        #self.Rollupd_MH : self.Rollupd_MH
                                        },
                    fallbacks = [MessageHandler((Filters.command ),self.ivday)],
                   
                    name= "dailyttcov",
                    persistent=True
                )

        # Set attendance conv

        Set_atdpa_cov = ConversationHandler(
                    entry_points=[MessageHandler(((Filters.regex(r"^[A-Za-z][A-Za-z][A-Za-z][A-Za-z][0-9][0-9]$") | 
                                    Filters.regex(r"^[Ee][0-9]$") | Filters.regex(r"^T&P$") ) ),self.selsubatd)],
                    states= {
                    self.Set_Atdpa_MH : [MessageHandler(((Filters.text("Present") | Filters.text("Absent") |
                                        Filters.regex(r"^..:..$") | Filters.regex(r"..?:..?") ) & (~Filters.command)),self.setsubat),
                                        MessageHandler((Filters.text('Go to Menu')),self.menu)]
                    },
                    allow_reentry= True,
                    map_to_parent={self.Menu_opt_MH: self.Menu_opt_MH,self.Set_Atd_MH : self.Set_Atd_MH,
                                        #self.Rollupd_MH : self.Rollupd_MH
                                        },
                    fallbacks = [MessageHandler((Filters.command),self.ivatd)],
                    
                    name= "atdpacov",
                    persistent=True
                )
        Set_atd_cov = ConversationHandler(
                    entry_points=[MessageHandler((Filters.text("Set Attendance")),self.getsubkb)],
                    states= {
                        self.Set_Atd_MH : [Set_atdpa_cov,MessageHandler((Filters.text('Go to Menu')),self.menu)]
                    },
                    allow_reentry= True,
                    map_to_parent={self.Menu_opt_MH : self.Menu_opt_MH,
                                        #self.Rollupd_MH: self.Rollupd_MH
                                        },

                    fallbacks = [MessageHandler((Filters.command),self.ivsub)],
                    name= "atdcov",                    
                    persistent=True
                )

        # Menu conv
        
        Menu_cov = ConversationHandler(
                    entry_points=[MessageHandler((Filters.text('Go to Menu') | Filters.text('Cancel')) ,self.menu)],
                    states= {
                        self.Menu_opt_MH : [MessageHandler((Filters.text("Today's Timetable")),self.stdtdt),
                                                MessageHandler((Filters.text('Go to Menu')),self.menu),
                                                Daily_tt_cov,MessageHandler((Filters.text("Get Attendance")),self.getstdatd),
                                                Set_atd_cov,(MessageHandler(Filters.text('Change Your ROLL NO'),self.rollupd))]
                    },
                    allow_reentry= True,
                    map_to_parent={self.Rollupd_MH: self.Rollupd_MH},
                    fallbacks = [MessageHandler((Filters.command) & ~Filters.text('Cancel'),self.default)],
                    name= "menucov",
                    persistent=True
                )

        # Setup conv or Start conv

        Setup_cov = ConversationHandler(
                    entry_points=[CommandHandler('start', self.start)],
                    states={
                        self.Setup_MH : [(MessageHandler(Filters.regex(r'^[CcEe][SsCc][Ee][1-2][0-9][Uu]0[0-3][0-9]$'), self.rollno ))],
                        self.Rollupd_MH : [(MessageHandler(Filters.regex(r'^[CcEe][SsCc][Ee][1-2][0-9][Uu]0[0-3][0-9]$'), self.rollno )),
                                                Menu_cov]
                    },
                    allow_reentry= True,
                    fallbacks=[MessageHandler((Filters.command),self.ivroll)],
                    name= "setupcov",
                    persistent=True,
                )
        
        dp.add_handler(Setup_cov)
        dp.add_error_handler(self.error)
        # self.updater.start_polling()
        # print("Getting Updates of CR_ALT")
        # self.updater.idle()

    # Invalid input functions
    def error(self,update, context):
        """Log Errors caused by Updates."""
        logger.warning('caused error "%s"', context.error)


    def ivroll(self, update, context):
        ''' Function to send error when user enters Invalid Roll Number'''
        update.message.reply_text(text='''*Invalid Roll Number*''', parse_mode= 'Markdown')
        update.message.reply_text(text='''Please try again \n*Valid Roll Number* ''', parse_mode= 'Markdown')
        return self.Setup_MH

    def ivday(self, update, context):
        ''' Function to send error when user enters Invalid Day'''
        update.message.reply_text(text='''*Invalid Day*''', parse_mode= 'Markdown')
        update.message.reply_text(text='''Please select or send a \n*Valid Day*\n''', parse_mode= 'Markdown')
        update.message.reply_text(text=''' Please Choose from \nCustom keyboard''', parse_mode= 'Markdown')
        return self.Day_MH

    def ivsub(self, update, context):
        ''' Function to send error when user enters Invalid Subject'''
        update.message.reply_text(text='''*Invalid Subject*''', parse_mode= 'Markdown')
        update.message.reply_text(text='''Please select or send a \n*Valid Subject*\n''', parse_mode= 'Markdown')
        update.message.reply_text(text=''' Please Choose from \nCustom keyboard''', parse_mode= 'Markdown')
        return self.Set_Atd_MH

    def ivatd(self, update, context):
        ''' Function to send error when user 
            enters Invalid Option or pattern at attendance function'''
        update.message.reply_text(text='''*Invalid Option or Pattern*''', parse_mode= 'Markdown')
        update.message.reply_text(text='''Please Verify your the Pattern or Option\n''', parse_mode= 'Markdown')
        update.message.reply_text(text='''Send the attendance in this *pp:tt* pattern''', parse_mode= 'Markdown')
        return self.Set_Atdpa_MH

    def default(self, update, context):
        '''
            Default function, Executed when Bot get undesired input
        '''
        update.message.reply_text(text='''Please Send a \n*Valid Message or Command* ''', parse_mode= 'Markdown')
        update.message.reply_text(text='''Please prefer using\n*CUSTOM KEYBOARD* ''', parse_mode= 'Markdown')
        return self.Menu_opt_MH

        # self.menu(update,context)

    # Jobqueue Functions

    

    def callback_daily(self,context: telegram.ext.CallbackContext):
        '''
            Jobqueue's callback_daily function
        '''
        usrlst = self.db.getusrlst()
        self.usrcnt = len(usrlst)

        for i in usrlst:
            text = "*Today's Timetable*\n"+self.stdtt(i[0])
            context.bot.send_message(chat_id=i[0], text=text, parse_mode= 'Markdown')
            time.sleep(1)
        context.bot.send_message(chat_id="1122913247", text="Total no of users using\nCR ATL\n = *{}*".format(self.usrcnt), parse_mode= 'Markdown')

    # Setup Functions or Start Functions

    def start(self, update, context):
        '''
            Function to execute when /start is input and asks for user roll_no or id_no 
        '''
        roll_no = self.db.chkusr(update.effective_chat.id)
        if roll_no == None:
            update.message.reply_text(text='''Hi! {}'''.format(update.message.from_user.first_name), parse_mode= 'Markdown')
            update.message.reply_text(text='''Welcome to your Personal\nTimetable and attendance Manager - \n             " *CR ALT* "''', parse_mode= 'Markdown')
            update.message.reply_text(text='''Please enter  *YOUR IIITT ROLL NO* for Signing up''', parse_mode= 'Markdown')
            return self.Setup_MH
        else:
            update.message.reply_text(text='''Welcome! {}'''.format(update.message.from_user.first_name), parse_mode= 'Markdown')
            update.message.reply_text(text='''You have logged in with *{}*'''.format(roll_no), parse_mode= 'Markdown')
            update.message.reply_text("Click on *Go to Menu* to visit Menu", parse_mode= 'Markdown',reply_markup=telegram.ReplyKeyboardMarkup([["Go to Menu"]]))
            return self.Rollupd_MH

    def rollno(self, update, context):
        '''
            Function to link the roll number with chat id 
        '''
        rollno = self.db.usrsetup(update.effective_chat.id,(update.message.text).upper(),self.updusr)
        if rollno:
            self.updusr = False
            update.message.reply_text(text="Your Roll no {}, \n linked to your account \nSuccessfully".format(rollno))
            update.message.text = rollno
            return self.start(update, context)  
        else:
            return self.ivroll(update, context)

    def rollupd(self,update,context):
        '''
            Updates User roll no
        '''
        self.updusr = True
        update.message.reply_text("Please Enter Your *IIITT* roll no to login:", parse_mode= 'Markdown', reply_markup=telegram.ReplyKeyboardMarkup([["Cancel"]]))
        return self.Rollupd_MH

    # Menu Functions

    def menu(self, update, context):
        '''
            Default Menu Function
        '''
        logger.info("User %s is using CR ALT.", update.message.from_user.first_name)
        text = [["Today's Timetable","Daily Timetable"],["Get Attendance","Set Attendance"],["Change Your ROLL NO"]]
        if 'Subject' in context.user_data:
            del context.user_data['Subject']
        bot.send_message(chat_id=update.effective_chat.id, text='''Select an option from the\ngiven menu''', reply_markup=telegram.ReplyKeyboardMarkup(text))
        return self.Menu_opt_MH

    # Student timetable Functions

    def stdtt(self,chat_id,day= datetime.datetime.now().strftime("%A")):
        '''
            Return student Timetable as a string
        '''
        perlst=self.db.getStdtt(self.db.getusrgrd(chat_id),day)
        text = "Time     : Subject\n"
        for i in perlst:
            text = text + i[0] + " : " + i[1]+"\n"
        if len(text)>19:
            return text
        else:
            return "No Classes"
    
    def stdtdt(self, update, context):
        '''
            Sends today's Timetable to the student
        '''
        text = self.stdtt(update.effective_chat.id)
        if text == "No Classes":
            update.message.reply_text(text="No Classes Today")
            return self.Menu_opt_MH
        else:
            update.message.reply_text(text=text)
            return self.Menu_opt_MH

    def stddtt(self, update, context):
        '''
            Sends the Timetable of the given day to the student
        '''
        if (update.message.text).capitalize() in self.daylst:
            text = self.stdtt(update.effective_chat.id,(update.message.text).capitalize())
            if text == "No Classes":
                update.message.reply_text(text="No Classes on {}".format((update.message.text).capitalize()))
                return self.Day_MH
            else:
                update.message.reply_text(text=text)
                return self.Day_MH
        else:
            update.message.reply_text(text="No Classes on {}".format((update.message.text).capitalize()))
            return self.Day_MH
    
    def daykb (self, update, context):
        '''
            Send Days as keyboard
        '''
        text = [[self.daylst[0],self.daylst[1]],[self.daylst[2],self.daylst[3]],[self.daylst[4],self.daylst[5]]]
        update.message.reply_text(text='''Select a Day from the\ngiven list''', reply_markup=telegram.ReplyKeyboardMarkup(text))
        return self.Day_MH

    # Get student's Attendance Functions
    
    def getstdatd (self, update, context):
        '''
            sends student's attendance 
        '''
        atdlst = self.db.getstdatt(update.effective_chat.id)
        text = "Subject: pst : ttl : % : Bnk/atd\n"
        for i in atdlst:
            per = 0
            bnk = None
            if i[2] !=0 :
                per = (int(i[1])/int(i[2]))*100
                per = float("{:.1f}".format(per))
                if (per>75):
                    bnk = ((4/3)*int(i[1]))-int(i[2])
                    if float(int(bnk)) != bnk:
                        bnk = int(bnk)+1
                else:
                    bnk = (3*int(i[2])-4*int(i[1]))
            text = text + str(i[0]) + ' : ' + str(i[1]) + ' : ' + str(i[2]) + ' : ' + str(per) + " : " + str(bnk)+"\n"
        update.message.reply_text(text=text)
        return self.Menu_opt_MH

    # Set student's attendance Functions
        
    def getsubkb(self, update, context):
        '''
            Send subjects as keyboard
        '''
        sublst=self.db.getsubgrd(self.db.getusrgrd(update.effective_chat.id))
        text = [["Go to Menu"]]
        for i in sublst:
            text.append([i[0]])
        bot.send_message(chat_id=update.effective_chat.id, text='''Select a Subject from the\ngiven list''', reply_markup=telegram.ReplyKeyboardMarkup(text))
        return self.Set_Atd_MH
    
    def selsubatd(self, update, context):
        '''
            Asks user for the status of the given subject (Present,Absent)
        '''
        context.user_data['Subject'] = (update.message.text).upper()
        text = [["Present","Absent"],["Go to Menu"]]
        update.message.reply_text(text='''Select the status of {}\n '''.format((update.message.text).upper()), reply_markup=telegram.ReplyKeyboardMarkup(text))
        update.message.reply_text(text='''If you want to enter \nthe pnt and ttl class \nseperatly then enter\nThem in this pattern - \n *pp:tt* or *p:t* or *p:tt* \n(ex: 05:10)-\n5 out of 10 classes attended''', parse_mode= 'Markdown')
        return self.Set_Atdpa_MH

    def setsubat(self, update, context):
        '''
            Sets attendance for the given subjects
        '''
        try:
            subnm = context.user_data['Subject']
            del context.user_data['Subject']
        except:
            subnm = None
        if subnm:
            resp = update.message.text
            if resp == 'Present':
                self.db.setstdatt(update.effective_chat.id,subnm)
            elif resp == 'Absent':
                self.db.setstdatt(update.effective_chat.id,subnm,0,1)
            else:
                att = resp.split(':')
                try:
                    if (int(att[0]) > int(att[1])):
                        bot.send_message(chat_id=update.effective_chat.id, text="Sorry,Present classes can't be grater than total classes")
                        raise Exception("Sorry,Present classes can't be grater than total classes")
                    self.db.setstdatt(update.effective_chat.id,subnm,att[0],att[1])
                except:
                    bot.send_message(chat_id=update.effective_chat.id, text="Invalid Input, Try Again")
        self.getstdatd(update,context)
        return self.getsubkb( update, context)
        
if __name__ == '__main__':
    db = teleDb()
    hi = stdchat(db)