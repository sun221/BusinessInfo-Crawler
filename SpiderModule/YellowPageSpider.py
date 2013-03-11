#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
继承这个父类，主要需要按照具体情况重写的方法有：
getMax()
dealContactPage()
getPageUrls()
"""
import sys
sys.path.append("..")
from time import sleep
import urllib ,urllib2
import cookielib
import sqlite3
import re
from bs4 import BeautifulSoup
urllib2.socket.setdefaulttimeout(30)
import chardet
import threading

from InputModule import Inputs,FliterRegular

class YellowPageSpider():
    def __init__(self):
        #多线程
        self.lock=threading.RLock()

        #数据库连接
        self.con = sqlite3.connect('../database.db')
        self.cur = self.con.cursor()

        #基本属性
        self.htmlfile=""
        self.soup=""
        self.country=""
        self.category=""
        self.title=""
        self.url=""
        self.originurl = ''
        self.goalurl=""
        self.seed=""
        self.max=0
        self.maxitem=0
        self.pageItems=20
        self.waittime=300

        #要存入的参数
        self.keywords=[]
        self.categories=[]
        self.homepageUrls=[]
        self.urls=[]
        self.contacturls=[]
        self.countries=[]
        self.names=[]
        self.emails=[]
        self.addresses=[]
        self.tels=[]
        self.rawInformations=[]

        #浏览器伪装
        self.cj = cookielib.CookieJar()
        self.opener=urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        #self.opener.addheaders = [('User-agent', 'Opera/9.23')]
        self.opener.add_headers=[("User-Agent","Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.35 Safari/537.17")]
        urllib2.install_opener(self.opener)
        self.requset=urllib2.Request(self.url)

    def setOriginUrl(self,url):
        self.originurl = url

    def setCountry(self,country):
        self.country=country

    def setPageMaxItems(self,itemNumbers):
        self.pageItems=itemNumbers

    def getMax(self,tag="span",tagTitle="id",tagValue="numberOfFreeResults"):
        htmlfile=self.getpage(self.goalurl)
        soup=BeautifulSoup(htmlfile,'lxml')
        maxresults=soup.find(tag,{tagTitle:tagValue})
        if maxresults:
            result=maxresults.get_text()
            if result:
                self.maxitem=result

    def getpage(self,url):
        if not url.startswith("http"):
            return
        requset=urllib2.Request(url)
        i=0
        t=0
        htmlfile=""
        while t==0:
            try:
                htmlfile=urllib2.urlopen(requset).read()
                if htmlfile:
                    t=1
                    break
                else:
                    i+=1
            except :
                i+=1
            if i>=5:break

        #print self.htmlfile
        try:
            charset=chardet.detect(htmlfile)["encoding"]
            htmlfile=unicode(htmlfile,charset)
        except:
            pass
        return htmlfile

    def dealContactPage(self,url):
        if not url:
            self.lock.acquire()

            self.names.append("")
            self.homepageUrls.append("")
            self.addresses.append("")
            self.tels.append("")
            self.emails.append("")
            self.rawInformations.append("")

            self.lock.release()
            return

        htmlfile=self.getpage(url)
        #print htmlfile
        soup=BeautifulSoup(htmlfile,'lxml')

        companyname=soup.find_all("h2",{"class":"fn org"})
        emails=soup.find_all("a",{"href":re.compile(r"javascript:openMail(.*);",re.DOTALL)})
        addresses=soup.find_all("address",{"class":"street"})
        tels=soup.find_all("span",{"class":"phoneSpan"})
        rawinformations=soup.find_all("ul",{"id":"descriptionTools"})

        name=""
        if companyname:
            name=companyname[0].a.text.strip()

        address=""
        if addresses:
            address=addresses[0]["title"].strip()

        email=""
        if emails:
            maillist=re.findall(r"\w+(?:[-+.]\w+)*@\w+(?:[-.]\w+)*\.\w+(?:[-.]\w+)*",emails[0]["href"],re.DOTALL)
            if maillist:
                email=maillist[0]

        if tels:
            tel=tels[0].text.replace("&nbsp;"," ").strip()

        rawinformation=""
        if rawinformations:
            rawinformation=rawinformations[0].get_text().strip()

        self.lock.acquire()

        self.names.append(name)
        self.homepageUrls.append(url)
        self.addresses.append(address)
        self.tels.append(tel)
        self.emails.append(email)
        self.rawInformations.append(rawinformation)

        self.lock.release()

    def initList(self):
        self.keywords=[self.word for i in range(self.pageItems)]
        self.categories=[self.category for i in range(self.pageItems)]
        self.originurls=[]
        self.urls=[]
        self.contacturls=[]
        self.countries=[self.country for i in range(self.pageItems)]
        self.names=[]
        self.emails=[]
        self.addresses=[]
        self.tels=[]
        self.rawInformations=[]

    def buildInformationList(self):
        """
        处理公司的urls，多线程作业，获得完整信息
        """
        threads=[]
        for url in self.contacturls:
            t=threading.Thread(target=self.dealContactPage,args=(url,))
            t.setDaemon(True)
            threads.append(t)
            t.start()
        print "开始从数据库获取Url并获取具体公司信息中."
        for t in threads:
            t.join(self.waittime)
        print "成功获得这部分公司信息了。"

    def saveToUrlDB(self,onetuple,database="Urls_Amarillas"):
        """
        把单条的页面中的公司链接保存到数据库待处理
        不需要外部调用
        """
        sql='INSERT INTO  %s (Keyword,Title,Url,Country,Dealed,HaveForm) VALUES(?,?,?,?,?,?)' % database
        print "saving "+ onetuple[2]

        try:
            self.cur.execute(sql,onetuple)
        except BaseException,e:
            print e,"该数据已经存在数据库中"

    def saveUrlList(self):
        """
        把所有的页面中的公司链接保存到数据库待处理
        """
        count=len(self.contacturls)
        for i in range(0,count):
            self.saveToUrlDB((buffer(self.word),"",self.contacturls[i],self.country,"0",'0'))
        try:
            self.con.commit()
        except:
            print "该数据已经存在数据库中"

    def saveToInformationDB(self,onetuple):
        """
        把单条的页面中的公司信息保存到数据库
        不需要外部调用
        """
        if FliterRegular.mailFiltered(onetuple[5]):
            return
        sql='INSERT INTO Information (Keyword,Url,Homepage,Name,Country,Email,Address,Tel,RawInformation,SearchTimes) VALUES(?,?,?,?,?,?,?,?,?,?)'
        print onetuple[3]+": "+onetuple[5]+"\n  Address: "+onetuple[6]
        try:
            self.cur.execute(sql,onetuple)
        except BaseException,e:
            print e,"该数据已存在Information数据库中."

    def saveInforList(self,tupleList):
        """
        把所有的页面中的公司信息保存到数据库
        """
        count=len(tupleList)
        for i in range(0,count):
            self.saveToInformationDB(tupleList[i])

        try:
            self.con.commit()
        except BaseException,e:
            print e,"该数据已存在Information数据库中."

    def fetchFromDB(self,limit=10,database="Urls_Amarillas"):
        self.cur.execute("""SELECT * FROM %s WHERE Dealed=0 Limit %d""" % (database,limit))
        result=self.cur.fetchmany(limit)
        if result:
            for i in range(0,len(result)):
                try:
                    self.keywords.append(result[i][0])
                    self.urls.append(result[i][2])
                    self.contacturls.append(result[i][2])
                    self.countries.append(result[i][3])
                except:
                    print "finish!"
                    return False
            return True
        else:
            return False

    def updateUrlDB(self,database="Urls_Amarillas"):
        """
        更新数据库中处理过的Url信息
        """
        for url in self.urls:
            sql="""UPDATE %s SET Dealed="1" WHERE Url="%s" """ % (database,url)
            try:
                self.cur.execute(sql)
            except BaseException,e:
                print e,"无法更新Dealed参数 ."
        try:
            self.con.commit()
        except BaseException,e:
            print e,"无法更新Dealed参数 ."

    def getPageUrls(self,url,feature="more urchin gaf"):
        htmlfile=self.getpage(url)
        soup=BeautifulSoup(htmlfile,'lxml')
        infourls=soup.find_all("a",{"class":feature})
        if infourls:
            for infourl in infourls:
                self.contacturls.append(infourl["href"])

    def buildPageUrlList(self):
        self.contacturls=[]
        threads=[]
        for url in self.urls:
            t=threading.Thread(target=self.getPageUrls,args=(url,))
            t.setDaemon(True)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    def formUrl(self,wordTitle,word,pageTitle,page,locationTitle,location,haveLocation='0'):
        if haveLocation=='0':
            keyword={
                wordTitle:word,
                pageTitle:page
            }
        else:
            keyword={
                wordTitle:word,
                pageTitle:page,
                locationTitle:location
            }
        url=self.originurl + urllib.urlencode(keyword)
        return url

    def formTupleList(self):
        tupleList=[]
        #print len(self.keywords),len(self.urls),len(self.names),len(self.countries),len(self.emails),len(self.addresses),len(self.tels),len(self.rawInformations)

        for i in range(0,len(self.keywords)):
            try:
                keyword=self.keywords[i]
            except:
                keyword=""
            try:
                category=self.categories[i]
            except:
                category=""

            try:
                url=self.urls[i]
            except:
                url=""
            try:
                homepage=self.homepageUrls[i]
            except:
                homepage=""
            try:
                name=self.names[i]
            except:
                name=""
            try:
                country=self.countries[i]
            except:
                country=""
            try:
                email=self.emails[i]
            except:
                email=""
            try:
                address=self.addresses[i]
            except:
                address=""
            try:
                tel=self.tels[i]
            except:
                tel=""
            try:
                rawInformation=self.rawInformations[i]
            except:
                rawInformation=""
            searchTimes=0
            tupleList.append((keyword,
                              category,
                              url,
                              homepage,
                              name,
                              country,
                              email,
                              address,
                              tel,
                              rawInformation,
                              searchTimes)
            )

        return tupleList

    def printTotalResults(self,max,nowlocation=""):
        """
        第一次获取时需要知道一共有多少个结果数，如果有定义max，要进行处理
        """
        if nowlocation:
            self.goalurl=self.formUrl("looking_for",self.word,"page",self.page,"location",nowlocation,"1")
        else:
            self.goalurl=self.formUrl("looking_for",self.word,"page",self.page,"","","0")

        self.getMax()
        self.max=int(int(self.maxitem)/self.pageItems)+1
        try:
            if int(max)!=0:
                if int(max)<self.max :
                    self.max=int(max)
        except:
            pass
        print "there are %s results." % self.maxitem

    def mainGetUrls(self,word="led light bulbs",max=0,local=0,allInformationInList="1"):
        self.max=max
        self.word=word
        self.page=1
        self.goalurl=self.formUrl("looking_for",self.word,"page",self.page,"","","0")
        if  local=="1":
            locals=Inputs.getLocals()
            if locals:
                for l in locals:
                    print "正在获取地区："+l
                    self.printTotalResults(max)

                    print " 正在获取每一个分页的信息."
                    self.page=1
                    for p in range(1,self.max+1):
                        self.page=p
                        self.goalurl=self.formUrl("looking_for",self.word,"page",self.page,"location",l,"1")
                        url=self.goalurl
                        print "Now dealing Location ："+l
                        print "Dealing page: ",p
                        if allInformationInList=="1":
                            #全部信息都在列表页中
                            self.initList()
                            self.dealContactPage(self.goalurl)
                            tupleList=self.formTupleList()
                            self.saveInforList(tupleList)
                            print "分页: ",str(p)," 的信息已经处理完毕并写入数据库"
                        else:
                        #全部信息不都在列表页中，需要进入获取
                            self.getPageUrls(url)


                    if allInformationInList!="1":
                        print "已经获得了所有分页信息，准备写入Url数据库."
                        self.saveUrlList()
                        self.contacturls=[]
                    print "休息一分钟后继续获取下一个地区"
                    sleep(60)

                print "成功！"


        else:
            self.printTotalResults(max)

            print " 正在处理每一个分页的信息."
            self.page=1
            for p in range(1,self.max+1):
                self.page=p
                self.goalurl=self.formUrl("looking_for",self.word,"page",self.page,"","","0")
                url=self.goalurl
                print "Dealing page: ",p

                if allInformationInList=="1":
                    #全部信息都在列表页中
                    self.initList()
                    self.dealContactPage(self.goalurl)
                    tupleList=self.formTupleList()
                    self.saveInforList(tupleList)

                else:
                    #全部信息不都在列表页中，需要进入获取
                    self.getPageUrls(url)

            if allInformationInList!="1":
                print "已经获得了所有分页信息，准备写入Url数据库."
                self.saveUrlList()
                self.contacturls=[]

            print "成功！"

    def mainMiningUrlDB(self,threadLimit=10):
        if (not threadLimit)or threadLimit=="0":
            threadLimit=10
        while self.fetchFromDB(threadLimit):
            #开始多线程获取
            self.buildInformationList()
            #构成结果
            tupleList=self.formTupleList()
            #保存到列表
            self.saveInforList(tupleList)
            #更新到数据库
            self.updateUrlDB()
            self.initList()

    def main(self,max=0,local=0,threadlimit=10,allInformationInList="1"):
        print "程序开始运行："
        keys=Inputs.readKeywords()
        #开始对每个关键词进行处理
        for word in keys:
            print "正在处理的类别与关键词是",word
            self.category=word.split(":")[0]
            keyword=word.split(":")[1]
            self.mainGetUrls(keyword,max,local,allInformationInList)
        if allInformationInList!='1':
            self.mainMiningUrlDB(threadLimit)

        print "程序全部运行完毕，成功。"

if __name__ == "__main__":
    yellowpage=YellowPageSpider()

    max=raw_input("请输入你要获取的最大页数，默认值是:0,即可自动获取数并判断最大页 >>>")
    threadLimit=raw_input("请输入你要使用的线程数，默认值为：10 >>>")
    local=raw_input("是否查询Location.txt中的地区，是请输入1，不是请输入0，默认值为：0 >>>")

    yellowpage.setOriginUrl('http://www.amarillas.cl/buscar/')
    yellowpage.setCountry("CL")
    yellowpage.setPageMaxItems(35)

    yellowpage.main(max,threadLimit,local)