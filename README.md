# ModernCryptographyTestSys_BaseOnDjango
## a onlie exam system for modern cryptography.
### based on python2.7/django/mysql/semantic-ui/AES128-CBC/SHA256
### I offer 550 problems in problems.sql
### You can just use it after configuring below.

        sudo pip install django
        
        git clone git@github.com:DshtAnger/ModernCryptographyTestSys.git
        cd ModernCryptographyTestSys_BaseOnDjango
        
        python manage.py makemigration
        python manage.py migrate
        
        sudo service mysql start
        mysql -u USERNAME -p
            create database question_bank;
            use question_bank;
            source ./problems.sql
            exit
        
        python manage.py runserver
