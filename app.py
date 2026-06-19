from flask import Flask,request,redirect,url_for,render_template,jsonify,session,make_response,flash
from flask_session import Session
from otp import genotp
from cmail import sendmail
from stoken import endata,dndata
from  flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from mysql.connector import (connection)
import os
import razorpay
import pdfkit
import re
mydb=connection.MySQLConnection(user='root',host='localhost',password='Moin@1234',database='ecom2456')
BASE_DIR=os.path.abspath(os.path.dirname(__file__))
print(BASE_DIR)
UPLOAD_FOLDER=os.path.join(BASE_DIR,'static','uploads')
print(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS={"png",'jpeg',"jpg",'webp','gif'}
MAX_CONTENT_LENGTH=6*1024*1024
os.makedirs(UPLOAD_FOLDER,exist_ok=True)
client= razorpay.Client(auth=("rzp_test_SvX4Kevc36OfpP","wTagj98TooEr9hYX2o23Hi0I"))
app=Flask(__name__)
bcrypt=Bcrypt(app)
app.secret_key='code9090' 
app.config['SESSION_TYPE']='filesystem'
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH']=MAX_CONTENT_LENGTH
Session(app)
@app.route('/')
def index():
    return render_template('welcome.html')
@app.route('/home')
def home():
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(itemid),item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename from items')
        allitemsdata=cursor.fetchall()
        cursor.close()
    except Exception as e:
            print(e)
            flash('Could not fetch item details')
            return redirect(url_for('home'))
    else:
        return render_template('index.html',allitemsdata=allitemsdata)
@app.route('/admincreate',methods=['GET','POST'])
def admincreate():
    if request.method=="POST":
        admin_username=request.form['username']
        admin_email=request.form['email']
        admin_password=request.form['password']
        admin_address=request.form['address']
        admin_agree=request.form['agree']
        gotp=genotp()
        admin_data={'admin_username':admin_username,'admin_email':admin_email,'admin_password':admin_password,'admin_address':admin_address,'admin_agree':admin_agree,'admin_otp':gotp}
        subject=f"Admin OTP Verift"
        body=f"Use This OTP For Admin Verification:{gotp}"
        sendmail(to=admin_email,subject=subject,body=body)
        flash('The OTP has been send to given mail')
        return redirect(url_for('adminotpverify',serverdata=endata(admin_data)))
    return render_template('admincreate.html')   
@app.route('/adminotpverify/<serverdata>',methods=['GET','POST']) 
def adminotpverify(serverdata):
    if request.method=='POST':
        adminotp=request.form['otp']
        try:
            d_data=dndata(serverdata)
        except Exception as e:
            print(e)
            flash('Could not verify details')
            return redirect(url_for('admincreate'))
        if adminotp==d_data['admin_otp']:
            hash_password=bcrypt.generate_password_hash(d_data['admin_password']).decode('utf-8')
            print(hash_password)
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into admindata(adminid,admin_username,admin_useremail,admin_password,admin_address,admin_agree) values (uuid_to_bin(uuid()),%s,%s,%s,%s,%s)',[d_data['admin_username'],d_data['admin_email'],hash_password,d_data['admin_address'],d_data['admin_agree']])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('Could not store details')
                return redirect(url_for('adminotpverify',serverdata=serverdata))
            else:
                flash('admin registration successfull')
                return redirect(url_for('adminlogin'))
        else:
            flash('OTP was wrong')
            return redirect(url_for('adminotpverify',
            serverdata=serverdata))
    return render_template('adminotp.html')
@app.route('/adminlogin',methods=['GET','POST'])
def adminlogin():
    if request.method=='POST':
        login_email=request.form['email']
        login_password=request.form['password']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(admin_useremail) from admindata where admin_useremail=%s',[login_email])
            count_email=cursor.fetchone()
            if count_email:
                if count_email[0]==1:
                    cursor.execute('select admin_password from admindata where admin_useremail=%s',[login_email])
                    stored_password=cursor.fetchone()
                    if bcrypt.check_password_hash(stored_password[0],login_password):
                        session['admin']=login_email
                        return redirect(url_for('admindashboard'))
                    else:
                        flash('password is wrong')
                        return redirect(url_for('adminlogin'))
                elif count_email[0]==0:
                    flash('No email found')
                    return redirect(url_for('adminlogin'))
                else:
                    flash('Could not verify email')
                    return redirect(url_for('adminlogin'))
        except Exception as e:
            print(e)
            flash('Could not verify adminlogin')
            return redirect(url_for('adminlogin'))
        else:
            if count_email[0]==1:
                cursor.execute('select admin_password from admindata where admin_useremail=%s',[login_email])
                stored_password=cursor.fetchone()
                if bcrypt.check_password_hash(stored_password[0],login_password):
                    # session['user']=login_useremail
                    flash('user logged in successfully')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Password is wrong')
                    return redirect(url_for('adminlogin'))
            else:
                flash('Enter valid email for login')
                return redirect(url_for('adminlogin'))
    return render_template('adminlogin.html')
@app.route('/dashboard',methods=['GET','POST'])
def dashboard():
    return render_template('dashboard.html')
@app.route('/admindashboard')
def admindashboard():
    if not session.get('admin'):
        flash('login to access dashboard')
        return redirect(url_for('adminlogin'))
    return render_template('adminpanel.html')
def allowed_file(filename:str)->bool:
    return "." in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/additem',methods=['GET','POST'])
def additem():
    if not session.get('admin'):
        flash('login to access dashboard')
        return redirect(url_for('adminlogin'))
    if request.method=='POST':
        item_name=request.form['title']
        item_description=request.form['Description']
        item_about=request.form['About_item']
        item_quantity=request.form['quantity']
        item_price=request.form['price']
        item_category=request.form['category']
        item_imagedata=request.files['file']
        imagename=item_imagedata.filename
        if item_imagedata and imagename:
            if not allowed_file(imagename):
                flash('File type is not Allowed. pls give png,jpg,jpeg,gif,webp')
                return redirect(url_for('additem'))
            orig_secure=secure_filename(imagename)
            ext=os.path.splitext(orig_secure)[1]
            filename=genotp()+ext
            save_path=os.path.join(app.config['UPLOAD_FOLDER'],filename)
            try:
                item_imagedata.save(save_path)
            except Exception as e:
                print(e)
                flash('Could not save file data')
                return redirect(url_for('additem'))
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select adminid from admindata where admin_useremail=%s',[session.get('admin')])
                added_by=cursor.fetchone()
                if added_by:
                    cursor.execute('insert into items(itemid,item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename,added_by) values (uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s,%s,%s)',[item_name,item_description,item_about,item_price,item_quantity,item_category,filename,added_by[0]])
                    mydb.commit()
                    cursor.close()
            except Exception as e:
                print(e)
                flash('Could not store item details')
                if save_path:
                    os.remove(save_path)
                return redirect(url_for('additem'))
            else:
                flash('Item added sucessfully')
                return redirect(url_for('additem'))
    return render_template('additem.html')
@app.route('/viewallitems')
def viewallitems():
    if not session.get('admin'):
        flash('to access admin dashboard pls login')
        return redirect(url_for('adminlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select adminid from admindata where admin_useremail=%s',[session.get('admin')])
        added_by=cursor.fetchone()
        if added_by:
            cursor.execute('select bin_to_uuid(itemid),item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename from items where added_by=%s',[added_by[0]])
            allitemsdata=cursor.fetchall()
            cursor.close()
        else:
            flash('user not found')
            return redirect(url_for('admindashboard'))
    except Exception as e:
            print(e)
            flash('Could not fetch item details')
            return redirect(url_for('admindashboard'))
    else:
        return render_template('viewall_items.html',allitemsdata=allitemsdata)
@app.route('/viewitem/<itemid>')
def viewitem(itemid):
    if not session.get('admin'):
        flash('to access admin dashboard pls login')
        return redirect(url_for('adminlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select adminid from admindata where admin_useremail=%s',[session.get('admin')])
        added_by=cursor.fetchone()
        if added_by:
            cursor.execute('select bin_to_uuid(itemid),item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename from items where added_by=%s and itemid=uuid_to_bin(%s)',[added_by[0],itemid])
            itemdata=cursor.fetchone() 
            cursor.close()
        else:
            flash('user not found')
            return redirect(url_for('admindashboard'))
    except Exception as e:
        print(e)
        flash('Clould not fetch items details')
        return redirect(url_for('admindashboard'))
    else:
        return render_template('view_item.html',itemdata=itemdata)
@app.route('/deleteitem/<itemid>')
def deleteitem(itemid):
    if not session.get('admin'):
        flash('to access admin dashboard pls login')
        return redirect(url_for('adminlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select adminid from admindata where admin_useremail=%s',[session.get('admin')])
        added_by=cursor.fetchone()
        if not added_by:
            flash('user not found')
            return redirect(url_for('viewallitems'))
        userid=added_by[0]
        cursor.execute('select bin_to_uuid(itemid),item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename from items where added_by=%s and itemid=uuid_to_bin(%s)',[added_by[0],itemid])
        itemdata=cursor.fetchone() 
        if not itemdata:
            flash('could not fetch itemdata')
            return redirect(url_for('viewallitems'))
        img_name=itemdata[7]
        cursor.execute('delete from items where added_by=%s and itemid=uuid_to_bin(%s)',[userid,itemid])
        mydb.commit()
        cursor.close()
    except Exception as e:
        mydb.rollback()
        app.logger.exception(f'DB delete fail:{e}')
        return redirect(url_for('viewallitems'))
    try:
        filepath=os.path.join(app.config['UPLOAD_FOLDER'],img_name)
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        mydb.rollback()
        app.logger.warning(f'file deletion failed:{e}')
        return redirect(url_for('viewallitems'))
    flash('item deleted successfully')
    return redirect(url_for('viewallitems'))
@app.route('/updateitem/<itemid>', methods=['GET', 'POST'])
def updateitem(itemid):
    if not session.get('admin'):
        flash('To access dashboard please login')
        return redirect(url_for('adminlogin'))
    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute('select adminid from admindata where admin_useremail=%s',[session.get('admin')])
        added_by = cursor.fetchone()
        if not added_by:
            flash('User not found')
            return redirect(url_for('admindashboard'))
        cursor.execute('''select bin_to_uuid(itemid),item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename from items where added_by=%s and itemid=uuid_to_bin(%s)''',[added_by[0], itemid])
        itemdata = cursor.fetchone()
        cursor.close()
        if not itemdata:
            flash('Item not found')
            return redirect(url_for('viewallitems'))
    except Exception as e:
        print(e)
        flash('Could not fetch item details')
        return redirect(url_for('admindashboard'))
    if request.method == 'POST':
        updateditem_name = request.form['title']
        updateditem_description = request.form['Description']
        updateditem_about = request.form['About_item']
        updateditem_quantity = request.form['quantity']
        updateditem_price = request.form['price']
        updateditem_category = request.form['category']
        updateditem_imagedata = request.files['file']
        updatedimagename = updateditem_imagedata.filename
        filename = itemdata[7]
        if updatedimagename:
            if not allowed_file(updatedimagename):
                flash('File type not allowed')
                return redirect(url_for('updateitem', itemid=itemid))
            orig_secure = secure_filename(updatedimagename)
            ext = os.path.splitext(orig_secure)[1]
            filename = genotp() + ext
            save_path = os.path.join(app.config['UPLOAD_FOLDER'],filename)
            try:
                updateditem_imagedata.save(save_path)
            except Exception as e:
                print(e)
                flash('Could not save image')
                return redirect(url_for('updateitem', itemid=itemid))
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('''update items set item_name=%s,item_description=%s,item_about=%s,item_price=%s,item_quantity=%s,item_category=%s,item_filename=%s where added_by=%sand itemid=uuid_to_bin(%s)''',[updateditem_name,updateditem_description,updateditem_about,updateditem_price,updateditem_quantity,updateditem_category,filename,added_by[0],itemid])
            mydb.commit()
            cursor.close()
        except Exception as e:
            print(e)
            if 'save_path' in locals() and os.path.exists(save_path):
                os.remove(save_path)
            flash('Could not update item')
            return redirect(url_for('updateitem', itemid=itemid))
        flash('Item updated successfully')
        return redirect(url_for('viewallitems'))
    return render_template('updateitem.html',itemdata=itemdata)
@app.route('/adminupdateprofile',methods=['GET','POST'])
def adminprofileupdate():
    if not session.get('admin'):
        flash('to access admin dashboard pls login')
        return redirect(url_for('adminlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select adminid,admin_username,admin_address,admin_phone,admining from admindata where admin_useremail=%s',[session.get('admin')])
        admin_data=cursor.fetchone()
    except Exception as e:
        print(e)
        flash('could not fetch admin details')
        return redirect(url_for('admindashboard'))
    else:
        if request.method=='POST':
            update_username=request.form['adminname']
            update_address=request.form['address']
            update_phonenumber=request.form['ph_no']
            updated_profiledata=request.files['file']
            print(updated_profiledata)
            filename=updated_profiledata.filename
            if filename == '' or filename is None:
                filename=admin_data[4]
            else:
                if updated_profiledata and filename:
                    if not allowed_file(filename):
                        flash('File type is not allowed. pls give png,jpg,jpeg,webp')
                        return redirect(url_for('adminprofileupdate'))
                    orig_secure=secure_filename(filename)
                    ext=os.path.splitext(orig_secure)[1]
                    filename=genotp()+ext
                    save_path=os.path.join(app.config['UPLOAD_FOLDER'],filename)
                    try:
                        updated_profiledata.save(save_path)
                        if admin_data[4]:
                            remove_path=os.path.join(app.config['UPLOAD_FOLDER'],admin_data[4])
                            os.remove(remove_path)
                    except Exception as e:
                        print(e)
                        flash('Could not add file')
                        return redirect(url_for('adminprofileupdate'))
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update admindata set admin_username=%s,admin_address=%s,admin_phone=%s,admining=%s where adminid=%s',[update_username,update_address,update_phonenumber,filename,admin_data[0]])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('DB error could not update data')
                return redirect(url_for('adminprofileupdate'))
            else:
                flash('Profile updated successfully')
                return redirect(url_for('adminprofileupdate'))
        return render_template('adminupdate.html',admin_data=admin_data)
@app.route('/adminlogout')
def adminlogout():
    if not session.get('admin'):
        flash('To access admin dashboard pls login')
        return redirect(url_for('adminlogin'))
    session.pop('admin')
    session.modified=True
    return redirect(url_for('adminlogin'))
@app.route('/usercreate',methods=['GET','POST'])
def usercreate():
    if request.method=='POST':
        username=request.form['name']
        email=request.form['email']
        password=request.form['password']
        address=request.form['address']
        usergender=request.form['usergender']
        user_phone=request.form['phone_no']
        gotp=genotp() #generates dynamic otp
        user_data={'username':username,'user_email':email,'user_password':password,'user_address':address,'user_gender':usergender,'user_phone':user_phone,'server_otp':gotp}
        subject=f"User OTP verify "
        body=f"Use the OTP :{gotp}"
        sendmail(to=email,subject=subject,body=body)
        flash('otp has been sent to given mail')
        return redirect(url_for('userotpverify',serverdata=endata(user_data)))
    return render_template('usersignup.html')
@app.route('/userotpverify/<serverdata>',methods=['GET','POST'])
def userotpverify(serverdata):
    if request.method=='POST':
        userotp=request.form['otp']
        try:
            d_data=dndata(serverdata)
        except Exception as e:
            print(e)
            flash('Could not verify details')
            return redirect(url_for('usercreate'))
        if userotp==d_data['server_otp']:
            hash_password=bcrypt.generate_password_hash(d_data['user_password'])
            print(hash_password)
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into userdata(userid,username,useremail,userpassword,useraddress,usergender,user_phone) values(uuid_to_bin(uuid()),%s,%s,%s,%s,%s,%s)',[d_data['username'],d_data['user_email'],hash_password,d_data['user_address'],d_data['user_gender'],d_data['user_phone']])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('Could not store details')
                return redirect(url_for('userotpverify',serverdata=serverdata))
            else:
                flash('user registration successfull')
                return redirect(url_for('userlogin'))
        else:
            flash('OTP was wrong ')
            return redirect(url_for('userotpverify',serverdata=serverdata))
    return render_template('userotp.html')
@app.route('/userlogin', methods=['GET', 'POST'])
def userlogin():
    if request.method == 'POST':
        login_email = request.form['email']
        login_password = request.form['password']
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('SELECT userpassword FROM userdata WHERE useremail=%s LIMIT 1',
                [login_email])
            stored_password = cursor.fetchone()
            print("EMAIL:", login_email)
            print("USER FOUND:", stored_password is not None)
            if stored_password:
                if bcrypt.check_password_hash(stored_password[0],login_password):
                    session['user'] = login_email
                    if login_email not in session:
                        session[login_email] = {}
                    flash('Login successful')
                    return redirect(url_for('home'))
                else:
                    flash('Password is wrong')
                    return redirect(url_for('userlogin'))
            else:
                flash('No email found')
                return redirect(url_for('userlogin'))
        except Exception as e:
            print("LOGIN ERROR:", e)
            flash('Could not verify user login')
            return redirect(url_for('userlogin'))
    return render_template('userlogin.html')
@app.route('/category/<ctype>')
def category(ctype):
    try:
        cursor=mydb.cursor(buffered=True)
        
        cursor.execute('select bin_to_uuid(itemid),item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename from items where item_category=%s',[ctype])
        itemsdata=cursor.fetchall() 
        cursor.close()
    except Exception as e:
        print(e)
        flash('Clould not fetch items details')
        return redirect(url_for('home'))
    else:
        return render_template('dashboard.html',itemsdata=itemsdata)
@app.route('/addcart/<itemid>')
def addcart(itemid):
    if not session.get('user'):
        flash('pls login to addcart')
        return redirect(url_for('home'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(itemid),item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename from items where itemid=uuid_to_bin(%s)',[itemid])
        item_data=cursor.fetchone()
        cursor.close()
    except Exception as e:
        print(e)
        flash('Could not fetch the item details')
        return redirect(url_for('home'))
    else:
        print(session,'before add-to-cart')
        if itemid not in session.get(session.get('user')):
            session[session.get('user')][itemid]=[item_data[1],1,item_data[4],item_data[5],item_data[6],item_data[7]]
            session.modified=True
            print(session,'after add-to-cart')
            flash('item added to cart')
            return redirect(url_for('home'))
        else:
            session[session.get('user')][itemid][1]+=1
            print(session,'already in cart')
            flash('item already in cart')
            return redirect(url_for('home'))
@app.route('/userlogout')
def userlogout():
    if session.get('user'):
        session.pop('user')
        flash('Logged out successfully')
        return redirect(url_for('home'))
    else:
        flash('Please login first')
        return redirect(url_for('home'))
@app.route('/viewcart')
def viewcart():
    if not session.get('user'):
        flash('pls login to view cart')
        return redirect(url_for('home'))
    try:
        cart=session[session.get('user')]
        if not cart:
            flash('No items in cart')
            return redirect(url_for('home'))
        subtotal=0
        items_for_display=[]
        for i,j in cart.items():
            itemid=i
            item_name=j[0]
            item_quantity=int(j[1])
            item_price=float(j[2])
            item_category=j[4]
            item_imgname=j[5]
            subtotal=subtotal+item_price*item_quantity
            items_for_display.append([itemid,item_name,item_quantity,item_price,item_category,item_imgname,subtotal])
        delivery=40 #default amount
        tax=round(subtotal*0.05,2)
        grand_total=subtotal+delivery+tax
        return render_template('cart.html',delivery=delivery,tax=tax,grand_total=grand_total,items_for_display=items_for_display,subtotal=subtotal)
    except Exception as e:
        print(e)
        flash('Could not fetch cart items')
        return render_template(url_for('home'))
@app.route('/updatecart/<itemid>', methods=['POST'])
def updatecart(itemid):
    if not session.get('user'):
        flash('Please log in to update your cart.')
        return redirect(url_for('home'))
    try:
        updated_quantity = int(request.form.get('quantity'))
        if itemid in session.get(session.get('user')):
            session.get(session.get('user'))[itemid][1] = updated_quantity
            session.modified = True
            flash('Cart updated successfully.')
            return redirect(url_for('viewcart'))
        else:
                flash('Item not found in cart.')
                return redirect(url_for('viewcart'))
    except Exception as e:
        print('error updating cart:',str(e))
        flash('Could not update cart. Please try again.')
        return redirect(url_for('home'))
@app.route('/removecart/<itemid>')
def removecart(itemid):
    if not session.get('user'):
        flash('Pls login to remove cart items')
        return redirect(url_for('userlogin'))
    try:
        if itemid in session.get(session.get('user')):
            session[session.get('user')].pop(itemid)
            session.modified=True
            flash('Cart item deleted successfully')
            return redirect(url_for('viewcart'))
        else:
            flash('Item not found in cart')
            return redirect(url_for('viewcart'))
    except Exception as e:
        print('error in item delete',str(e))
        flash('Could not delete cart item')
        return redirect(url_for('home'))
@app.route('/paycart',methods=['GET','POST'])
def paycart():
    if not session.get('user'):
        flash('pls login to buy items')
        return redirect(url_for('home'))
    try:
        cart=session.get(session.get('user'),{})
        #only use single_buy if explicitly coming from buynow route
        cart_mode='cart'
        if request.args.get('type')=='single':
            cart=session.get('single_buy',{})
            cart_mode='single'
        else:
            if 'single_buy' in session:
                session.pop('single_buy')
                session.modified=True
                cart_mode='cart'
        print(cart_mode,cart)
        if not cart:
            flash('NO item assigned')
            return redirect(url_for('home'))
        subtotal=0
        items_data=[]
        for i, j in cart.items():
            itemid=i
            itemname=j[0]
            itemquantity = int(j[1])
            itemprice=float(j[2])
            item_category = j[4]
            itemimg=j[5]
            amount=itemquantity*itemprice
            subtotal=subtotal+itemquantity*itemprice
            items_data.append([itemid,itemname,itemquantity,itemprice,item_category,itemimg,amount])
        delivery=40
        tax=round(subtotal*0.05,2)
        grand_total = delivery + tax + subtotal
        razorpay_amount = int(grand_total * 100)
        order=client.order.create({
            "amount": razorpay_amount,
            "currency":"INR",
            "receipt":f"{session.get('user')}",
            "payment_capture": 1
        })
        print('order created successfully',order)
        return render_template('pay.html',order=order,
        items_data=items_data,delivery=delivery,tax=tax,
        grand_total=grand_total,cart_mode=cart_mode)
    except Exception as e:
        print(e)
        flash('Could not create order')
        return redirect(url_for('home'))
@app.route('/success_cart',methods=['POST'])
def success_cart():
    try:
        payment_id=request.form['razorpay_payment_id']
        order_id=request.form['razorpay_order_id']
        signature=request.form['razorpay_signature']
        amount=float(request.form['grand_total'])
        mode=request.form['mode'] #'single' or 'cart'
        #verify payment signature
        param_dict = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature}
        try:
            client.utility.verify_payment_signature(param_dict)
        except Exception as e:
            print(e)
            flash('Verification failed')
            return redirect(url_for('home'))
        cart=session.get(session.get('user'),{})
        if mode=='single':
            cart=session.get('single_buy',{})
        else:
            if 'single_buy' in session:
                session.pop('single_buy')
                session.modified=True
            cart=session.get(session.get('user'),{})
        if not cart:
            flash('No details in cart')
            return redirect(url_for('home'))
        print(cart.values())
        items_total=sum(float(v[2]) * int(v[1]) for v in cart.values())
        delivery=40
        tax=round(items_total*0.05,2)
        grand_total=items_total+delivery+tax
        print(amount,grand_total)
        if amount==grand_total:
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
                userid=cursor.fetchone()[0]
                cursor.execute('insert into orders(razorpay_orderid,razorpay_paymentid,userid,total_amount,delivery,tax,grand_total) values(%s,%s,%s,%s,%s,%s,%s)',[order_id,payment_id,userid,items_total,delivery,tax,grand_total])
                order_table_id=cursor.lastrowid
                insert_itemdetails = '''
                insert into order_items_details
                (ordid,itemid,item_name,item_price,item_quantity,subtotal,item_category,item_imgname)
                values(%s,uuid_to_bin(%s),%s,%s,%s,%s,%s,%s)
                '''
                for i,j in cart.items():
                    print(i)
                    itemid=i
                    itemname=j[0]
                    itemquantity=int(j[1])
                    itemprice=float(j[2])
                    item_category=j[4]
                    item_imgname=j[5]
                    amount=itemquantity*itemprice
                    cursor.execute(insert_itemdetails,[order_table_id,itemid,itemname,itemprice,itemquantity,amount,item_category,item_imgname])
                    cursor.execute('''update items set item_quantity = item_quantity - %s where itemid = uuid_to_bin(%s)''',[itemquantity, itemid])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print('Mysql Error:', str(e))
                flash('Could not store order details')
                return redirect(url_for('home'))
            #flush the cart details
            if mode=='single':
                if 'single_buy' in session:
                    session.pop('single_buy')
                    session.modified=True
            session[session.get('user')]={}
            flash('Order details successfully stored')
            return redirect(url_for('home'))
        else:
            flash('Amount invalid')
            return redirect(url_for('viewcart'))
    except Exception as e:
        print('payment failed',str(e))
        flash('Payment verification failed')
        return redirect(url_for('home'))
@app.route('/myorders')
def myorders():
    if not session.get('user'):
        flash('pls login to view orders')
        return redirect(url_for('home'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user=cursor.fetchone()[0]
        if user:
            cursor.execute('select * from orders where userid=%s order by created_at desc',[user])
            order_list=cursor.fetchall()
            cursor.close()
            return render_template('myorders.html',order_data=order_list)
        else:
            flash('could noty verify user')
            return redirect(url_for('home'))
    except Exception as e:
        print(e)
        flash('could get the list of orders')
        return redirect(url_for('home'))
@app.route('/myorder_details/<ordid>')
def myorder_details(ordid):
    if not session.get('user'):
        flash('pls login to view orders')
        return redirect(url_for('userlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user=cursor.fetchone()[0]
        if user:
            cursor.execute('select * from orders where userid=%s and orderid=%s',[user, ordid])
            order_data=cursor.fetchone()
            cursor.execute('select order_detailsid,ordid,bin_to_uuid(itemid),item_name,item_price,item_quantity,subtotal,item_category,item_imgname from order_items_details where ordid=%s',[ordid])
            ordered_items_list=cursor.fetchall()
            cursor.close()
            return render_template('order_details.html',order_data=order_data,ordered_items_list=ordered_items_list)
        else:
            flash('could not verify user')
            return redirect(url_for('home'))
    except Exception as e:
        print(e)
        flash('could not get the list of orders')
        return redirect(url_for('home'))
@app.route('/getinvoice/<int:ordid>')
def getinvoice(ordid):
    if not session.get('user'):
        flash('pls login to view orders')
        return redirect(url_for('userlogin'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('user')])
        user=cursor.fetchone()[0]
        if user:
            cursor.execute('select * from orders where userid=%s and orderid=%s',[user, ordid])
            order_data=cursor.fetchone()
            cursor.execute('select order_detailsid,ordid,itemid,item_name,item_price,item_quantity,subtotal,item_category,item_imgname from order_items_details where ordid=%s',[ordid])
            ordered_items_list=cursor.fetchall()
            cursor.close()
            html=render_template('invoice.html',order_data=order_data,ordered_items_list=ordered_items_list)
            #generating pdf using pdfkit
            config=pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
            pdf=pdfkit.from_string(html,False,configuration=config)
            response=make_response(pdf)
            response.headers['Content-Type']='application/pdf'
            response.headers['Content-Disposition']=(f'attachment; filename=invoice_{ordid}.pdf')
            return response
        else:
            flash('could not verify user')
            return redirect(url_for('home'))
    except Exception as e:
        print(e)
        flash('could not get the list of orders')
        return redirect(url_for('home'))
@app.route('/buy_now', methods=['POST'])
def buy_now():
    if 'user' not in session:
        flash('Please login first')
        return redirect(url_for('userlogin'))
    try:
        itemid = request.form['itemid']
        quantity = int(request.form['quantity'])
        cursor = mydb.cursor(buffered=True)
        cursor.execute('SELECT * FROM items WHERE itemid=UUID_TO_BIN(%s)',[itemid])
        item_data = cursor.fetchone()
        if not item_data:
            flash('Item not found')
            return redirect(url_for('home'))
        available_stock = int(item_data[5])
        if quantity < 1:
            quantity = 1
        if quantity > available_stock:
            flash(f'Only {available_stock} items available')
            return redirect(url_for('descitem', itemid=itemid))
        session['single_buy'] = {itemid: [item_data[1],      # item_name
                quantity,          # selected quantity
                float(item_data[4]), # price
                item_data[5],      # stock
                item_data[6],      # category
                item_data[7]       # image
            ]
        }
        session.modified = True
        return redirect(url_for('paycart', type='single'))
    except Exception as e:
        print("BUY NOW ERROR:", e)
        flash('Could not process Buy Now')
        return redirect(url_for('home'))
@app.route('/descitem/<itemid>')
def descitem(itemid):
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(itemid),item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename from items where itemid=uuid_to_bin(%s)',[itemid])
        itemdata=cursor.fetchone() 
        cursor.close()
    except Exception as e:
        print(e)
        flash('Clould not fetch items details')
        return redirect(url_for('home'))
    else:
        return render_template('desc.html',itemdata=itemdata)
@app.route('/addreview/<itemid>', methods=['GET', 'POST'])
def addreview(itemid):
    if not session.get('user'):
        flash('Please login first')
        return redirect(url_for('userlogin'))
    if request.method == 'POST':
        review_text = request.form['review_text']
        review_rating = request.form['rating']
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute(
                'select userid from userdata where useremail=%s',
                [session.get('user')])
            user = cursor.fetchone()
            if user:
                cursor.execute('''insert into item_reviews(review_text, rating, itemid, userid)values (%s, %s, uuid_to_bin(%s), %s)''',[review_text, review_rating, itemid, user[0]])
                mydb.commit()
                cursor.close()
            else:
                flash('User not found')
                return redirect(url_for('descitem', itemid=itemid))
        except Exception as e:
            print(e)
            flash('Could not save review')
            return redirect(url_for('descitem', itemid=itemid))
        flash('Review added successfully')
        return redirect(url_for('descitem', itemid=itemid))
    return render_template('addreview.html', itemid=itemid)
@app.route('/readreview/<itemid>')
def readreview(itemid):
    try:
        cursor = mydb.cursor(buffered=True)
        # Fetch item details
        cursor.execute("""SELECT bin_to_uuid(itemid),item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename FROM items WHERE itemid = uuid_to_bin(%s)""", [itemid])
        item_data = cursor.fetchone()
        # Fetch reviews
        cursor.execute("""SELECT item_reviews.review_text,item_reviews.rating,userdata.username FROM item_reviews JOIN userdata ON item_reviews.userid = userdata.userid WHERE item_reviews.itemid = uuid_to_bin(%s)""", [itemid])
        reviews = cursor.fetchall()
        cursor.close()
        return render_template('read_review.html',reviews=reviews,item_data=item_data,itemid=itemid)
    except Exception as e:
        print("READ REVIEW ERROR:", e)
        flash("Could not fetch reviews")
        return redirect(url_for('descitem', itemid=itemid))
@app.route('/usernewpassword/<data>', methods=['GET', 'POST'])
def usernewpassword(data):
    if request.method == 'POST':
        try:
            forgot_email = dndata(data)
            new_password = request.get_json()['new_password']
            hash_password = bcrypt.generate_password_hash(new_password)
            cursor = mydb.cursor(buffered=True)
            cursor.execute('update userdata set userpassword=%s where useremail=%s',[hash_password, forgot_email])
            mydb.commit()
            cursor.close()
            return jsonify({"message": "Password updated successfully"})
        except Exception as e:
            print("PASSWORD UPDATE ERROR:", e)
            return jsonify({"error": "Password update failed"}), 500
    return render_template('usernewpassword.html', data=data)
@app.route('/userforgotpassword', methods=['GET', 'POST'])
def userforgotpassword():
    if request.method == 'POST':
        forgot_email = request.form['email']
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute(
                'SELECT * FROM userdata WHERE useremail=%s',
                [forgot_email])
            data = cursor.fetchone()
            if data:
                reset_link = url_for('usernewpassword',data=endata(forgot_email),_external=True)
                subject = "User Password Reset"
                body = f""" Hello, Click the link below to reset your password: {reset_link} If you did not request this password reset, please ignore this email."""
                sendmail(to=forgot_email,subject=subject,body=body)
                flash('Reset link has been sent to your email')
                return redirect(url_for('userforgotpassword'))
            else:
                flash('No Email found. Please check.')
                return redirect(url_for('userforgotpassword'))
        except Exception as e:
            print(e)
            flash('Could not send reset link')
            return redirect(url_for('userforgotpassword'))
    return render_template('userforgot.html')
@app.route('/usersearch', methods=['POST'])
def usersearch():
    searchdata = request.form['q'].strip()
    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute('''select bin_to_uuid(itemid),item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename from items where item_name like %s or item_description like %s or item_about like %s or item_category like %s''',[f'%{searchdata}%',f'%{searchdata}%',f'%{searchdata}%',f'%{searchdata}%'])
        allitemsdata = cursor.fetchall()
        cursor.close()
        return render_template('index.html',allitemsdata=allitemsdata)
    except Exception as e:
        print("USER SEARCH ERROR:", e)
        flash('Search failed')
        return redirect(url_for('home'))
@app.route('/adminsearch', methods=['POST'])
def adminsearch():
    if not session.get('admin'):
        flash('Please login as admin')
        return redirect(url_for('adminlogin'))
    searchdata = request.form['q'].strip()
    try:
        cursor = mydb.cursor(buffered=True)
        cursor.execute('''select bin_to_uuid(itemid),item_name,item_description,item_about,item_price,item_quantity,item_category,item_filename from items where item_name like %s or item_description like %s or item_about like %s or item_category like %s''',[f'%{searchdata}%',f'%{searchdata}%',f'%{searchdata}%',f'%{searchdata}%'])
        allitemsdata = cursor.fetchall()
        cursor.close()
        return render_template('viewall_items.html',allitemsdata=allitemsdata)
    except Exception as e:
        print(e)
        flash('Search failed')
        return redirect(url_for('viewallitems'))
@app.route('/adminforgotpassword', methods=['GET', 'POST'])
def adminforgotpassword():
    if request.method == 'POST':
        forgot_email = request.form['forgot_email']
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('select count(*) from admindata where admin_useremail=%s',[forgot_email])
            count_email = cursor.fetchone()[0]
            if count_email == 1:
                subject = "Admin Password Reset"
                body = f"Reset Link : {url_for('adminnewpassword', data=endata(forgot_email), _external=True)}"
                sendmail(to=forgot_email,subject=subject,body=body)
                flash('Reset link sent successfully')
                return redirect(url_for('adminforgotpassword'))
            else:
                flash('Email not found')
                return redirect(url_for('adminforgotpassword'))
        except Exception as e:
            print(e)
            flash('Could not send reset link')
            return redirect(url_for('adminforgotpassword'))
    return render_template('adminforgotpwd.html')
@app.route('/adminnewpassword/<data>', methods=['GET', 'POST'])
def adminnewpassword(data):
    if request.method == 'POST':
        try:
            admin_email = dndata(data)
            new_password = request.get_json()['new_password']
            hash_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            cursor = mydb.cursor(buffered=True)
            cursor.execute('''update admindata set admin_password=%s where admin_useremail=%s''',[hash_password, admin_email])
            mydb.commit()
            cursor.close()
            return jsonify({"message": "Password updated successfully"})
        except Exception as e:
            print(e)
            return jsonify({"message": "Password update failed"})
    return render_template('adminnewpassword.html', data=data)
@app.route('/contactus', methods=['GET', 'POST'])
def contactus():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        try:
            cursor = mydb.cursor(buffered=True)
            cursor.execute('''INSERT INTO contact_messages(name,email,subject,message) VALUES(%s,%s,%s,%s)''',[name, email, subject, message])
            mydb.commit()
            print("CONTACT MESSAGE SAVED")
            try:
                print("SENDING CONTACT EMAIL...")
                sendmail(to="moinuddinchistyshaik@gmail.com",subject=f"BUYROUTE Contact: {subject}",body=f"""New Contact Form Submission Name: {name} Email: {email} Subject: {subject} Message:{message}""")
                print("CONTACT EMAIL SENT SUCCESSFULLY")
            except Exception as mail_error:
                print("CONTACT MAIL ERROR:", mail_error)
            cursor.close()
            flash('Message sent successfully')
            return redirect(url_for('contactus'))
        except Exception as e:
            print("CONTACT FORM ERROR:", e)
            flash('Could not send message')
            return redirect(url_for('contactus'))
    return render_template('contactus.html')
@app.route('/viewcontacts')
def viewcontacts():
    if 'admin' not in session:
        flash('Please login as admin')
        return redirect(url_for('adminlogin'))
    cursor = mydb.cursor(buffered=True)
    cursor.execute('''SELECT * FROM contact_messages ORDER BY created_at DESC''')
    contacts = cursor.fetchall()
    cursor.close()
    return render_template('viewcontacts.html',contacts=contacts)
app.run(debug=True,use_reloader=True)