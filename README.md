# ModernCryptographyTestSys_BaseOnDjango
## a onlie exam system for modern cryptography.
### based on python2.7/django/mysql/semantic-ui/AES128-CBC/SHA256
### I offer 550 problems in problems.sql
### You can just use it after configuring below.(ubuntu 14.x x64)

        git clone git@github.com:DshtAnger/Modern_Cryptography_TestSys.git
        
        sudo apt-get install apache2
        sudo apt-get install libapache2-mod-wsgi
        sudo apt-get install mysql-server
        sudo apt-get install mysql-client
        sudo apt-get install libmysqlclient-dev
        sudo apt-get install python-mysqldb
        
        sudo apt-get install python-pip
        sudo apt-get install django
        
        unzip Crypto.zip
        mv Crypto /usr/lib/python2.7/dist-packages/
        mv exam_system.conf /etc/apache2/site-available/
        
        mysql -u root -p
                create database YOUR_DATABASE_NAME
                exit
                
        cd Modern_Cryptography_TestSys
        python manage.py makemigrations
        python manage.py migrate
        python manage.py createcachetable YOUR_CACHE_NAME
        
        mysql -u root -p
                use question_bank;
                source problems.sql;
                exit
        
        chmod 755 /root
        chmod -R 644 Modern_Cryptography_TestSys
        find Modern_Cryptography_TestSys -type d -exec chmod 755 \{\} \;
        chmod a+w Modern_Cryptography_TestSys/examination/templates/exams_results
        
        a2ensite exam_system
        service apache2 restart
