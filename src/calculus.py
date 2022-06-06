#!/usr/bin/env python
# -*- coding: utf-8 -*-

import calculus_functions as cf
import calculus_ll as cll
import numpy as np
import time
import debug
import os

class gradient:
	
	def __init__(self,panel,callback):
		self.panel=panel
		self.callback=callback
		
	def arima_grad(self,k,x,ll,sign,pre):
		if k==0:
			return None
		(N,T,m)=x.shape
		x=self.panel.arma_dot.dotroll(pre,k,sign,x,ll)
		x.resize(N,T,k)
		extr_value=1e+100
		if np.max(np.abs(x))>extr_value:
			x[np.abs(x)>extr_value]=np.sign(x[np.abs(x)>extr_value])*extr_value
		return x*self.panel.a[3]

	def garch_arima_grad(self,ll,d,dRE,varname):
		panel=self.panel
		groupeffect=0
		groupeffect, dvRE_dx=None, None
		d_input=0
		if self.panel.N>1 and panel.options.fixed_random_group_eff.value>0 and not dRE is None:
			d_eRE_sq=2*ll.e_RE*dRE
			dmeane2=panel.mean(d_eRE_sq,(0,1))
			d_input=(d_eRE_sq-dmeane2)*panel.a[3]
			dvRE_dx=dmeane2*panel.a[3]-ll.re_obj_i_v.dRE(d_input,ll.varRE_input,varname,panel)-ll.re_obj_t_v.dRE(d_input,ll.varRE_input,varname,panel)
			groupeffect=ll.dlnvRE*dvRE_dx*panel.a[3]
		
		if (not panel.options.RE_in_GARCH.value):
			dRE=d
		dlnv_sigma_G=None
		if self.panel.pqdkm[4]>0 and not dRE is None: 			#eqs. 33-34
			((N,T,k))=dRE.shape
			x=cf.prod((ll.h_e_val,dRE))	
			dlnv_sigma_G=self.panel.arma_dot.dot(ll.GAR_1MA,x,ll)
		dlnv_e=cf.add((dlnv_sigma_G,groupeffect),True)
		return dlnv_e,dlnv_sigma_G,dvRE_dx,d_input


	def get(self,ll,DLL_e=None,dLL_lnv=None,return_G=False):
		if not self.callback(0.05,'',task='gradient'):return None, g
		(self.DLL_e, self.dLL_lnv)=(DLL_e, dLL_lnv)
		panel=self.panel
		incl=self.panel.included[3]
		re_obj_i,re_obj_t=ll.re_obj_i,ll.re_obj_t
		u,e,h_e_val,lnv_ARMA,h_val,v=ll.u,ll.e,ll.h_e_val,ll.lnv_ARMA,ll.h_val,ll.v
		p,q,d,k,m=panel.pqdkm
		nW=panel.nW
		if DLL_e is None:
			dLL_lnv, DLL_e=cll.gradient(ll,self.panel)
		#ARIMA:
		de_rho=self.arima_grad(p,u,ll,-1,ll.AMA_1)
		de_lambda=self.arima_grad(q,e,ll,-1,ll.AMA_1)
		de_beta=-self.panel.arma_dot.dot(ll.AMA_1AR,panel.XIV,ll)*panel.a[3]
		
		(self.de_rho,self.de_lambda,self.de_beta)=(de_rho,de_lambda,de_beta)
		
		self.de_rho_RE       =    cf.add((de_rho,     re_obj_i.dRE(de_rho, ll.e,'rho',panel), 		re_obj_t.dRE(de_rho,ll.e,'rho',panel)), True)
		self.de_lambda_RE    =    cf.add((de_lambda,  re_obj_i.dRE(de_lambda, ll.e,'lambda',panel),	re_obj_t.dRE(de_lambda,ll.e,'lambda',panel)), True)
		self.de_beta_RE      =    cf.add((de_beta,    re_obj_i.dRE(de_beta, ll.e,'beta',panel), 		re_obj_t.dRE(de_beta,ll.e,'beta',panel)), True)		

		dlnv_sigma_rho,		dlnv_sigma_rho_G,		dvRE_rho	, d_rho_input		=	self.garch_arima_grad(ll,	de_rho,		self.de_rho_RE,		'rho')
		dlnv_sigma_lambda, 	dlnv_sigma_lambda_G,	dvRE_lambda	, d_lambda_input	=	self.garch_arima_grad(ll,	de_lambda,	self.de_lambda_RE,	'lambda')
		dlnv_sigma_beta,	dlnv_sigma_beta_G,		dvRE_beta	, d_beta_input		=	self.garch_arima_grad(ll,	de_beta,	self.de_beta_RE,	'beta')

		(self.dlnv_sigma_rho,self.dlnv_sigma_lambda,self.dlnv_sigma_beta)=(dlnv_sigma_rho,dlnv_sigma_lambda,dlnv_sigma_beta)
		(self.dlnv_sigma_rho_G,self.dlnv_sigma_lambda_G,self.dlnv_sigma_beta_G)=(dlnv_sigma_rho_G,dlnv_sigma_lambda_G,dlnv_sigma_beta_G)
		(self.dvRE_rho,self.dvRE_lambda,self.dvRE_beta)=(dvRE_rho,dvRE_lambda,dvRE_beta)
		(self.d_rho_input,self.d_lambda_input,self.d_beta_input)=(d_rho_input,d_lambda_input,d_beta_input)

		#GARCH:
		(dlnv_gamma, dlnv_psi, dlnv_mu, dlnv_z_G, dlnv_z)=(None,None,None,None,None)
		if panel.N>1:
			dlnv_mu=cf.prod((ll.dlnvRE_mu,incl))
		else:
			dlnv_mu=None	
			
		if m>0:
			dlnv_gamma=self.arima_grad(k,lnv_ARMA,ll,1,ll.GAR_1)
			dlnv_psi=self.arima_grad(m,h_val,ll,1,ll.GAR_1)
			if not ll.h_z_val is None:
				dlnv_z_G=cf.dot(ll.GAR_1MA,ll.h_z_val)
				(N,T,k)=dlnv_z_G.shape

			dlnv_z=dlnv_z_G


		(self.dlnv_gamma, self.dlnv_psi,self.dlnv_mu,self.dlnv_z_G,self.dlnv_z)=(dlnv_gamma, dlnv_psi, dlnv_mu, dlnv_z_G, dlnv_z)

		#LL

		#final derivatives:
		dLL_beta=cf.add((cf.prod((dlnv_sigma_beta,dLL_lnv)),cf.prod((self.de_beta_RE,DLL_e))),True)
		dLL_rho=cf.add((cf.prod((dlnv_sigma_rho,dLL_lnv)),cf.prod((self.de_rho_RE,DLL_e))),True)
		dLL_lambda=cf.add((cf.prod((dlnv_sigma_lambda,dLL_lnv)),cf.prod((self.de_lambda_RE,DLL_e))),True)
		dLL_gamma=cf.prod((dlnv_gamma,dLL_lnv))
		dLL_psi=cf.prod((dlnv_psi,dLL_lnv))
		self.dlnv_omega=panel.W_a
		dLL_omega=cf.prod((self.dlnv_omega,dLL_lnv))
		dLL_mu=cf.prod((self.dlnv_mu,dLL_lnv))
		dLL_z=cf.prod((self.dlnv_z,dLL_lnv))

		G=cf.concat_marray((dLL_beta,dLL_rho,dLL_lambda,dLL_gamma,dLL_psi,dLL_omega,dLL_mu,dLL_z))
		g=np.sum(G,(0,1))
		#For debugging:
		#print (g)
		#gn=debug.grad_debug(ll,panel,0.00001)#debugging
		#if np.sum((g-gn)**2)>10000000:
		#	a=0
		#print(gn)
		#a=debug.grad_debug_detail(ll, panel, 0.00000001, 'LL', 'beta',0)
		#dLLeREn,deREn=debug.LL_calc_custom(ll, panel, 0.0000001)
		if not self.callback(0.08,'','hessian'):return

		if return_G:
			return  g,G
		else:	
			return g


class hessian:
	def __init__(self,panel,g,callback):
		self.panel=panel
		self.its=0
		self.g=g
		self.callback=callback
		
	
	def get(self,ll,d2LL_de2,d2LL_dln_de,d2LL_dln2):	
		N,T,k=self.panel.X.shape
		return self.hessian(ll,d2LL_de2,d2LL_dln_de,d2LL_dln2)


	def hessian(self,ll,d2LL_de2,d2LL_dln_de,d2LL_dln2):
		panel=self.panel
		tic=time.perf_counter()
		g=self.g
		p,q,d,k,m=panel.pqdkm
		incl=self.panel.included[3]
		
		GARM=(cf.ARMA_product(ll.GAR_1,m,panel,ll,'m'),ll.GAR_1,m,1)
		
		GARK=(cf.ARMA_product(ll.GAR_1,k,panel,ll,'k'),ll.GAR_1,k,1)

		d2lnv_gamma2		=   cf.prod((2, 
		                        cf.dd_func_lags(panel,ll,GARK, 	g.dlnv_gamma,						g.dLL_lnv,  transpose=True)))
		d2lnv_gamma_psi		=	cf.dd_func_lags(panel,ll,GARK, 	g.dlnv_psi,							g.dLL_lnv)

		d2lnv_gamma_rho		=	cf.dd_func_lags(panel,ll,GARK,	g.dlnv_sigma_rho_G,						g.dLL_lnv)
		d2lnv_gamma_lambda	=	cf.dd_func_lags(panel,ll,GARK, 	g.dlnv_sigma_lambda_G,					g.dLL_lnv)
		d2lnv_gamma_beta	=	cf.dd_func_lags(panel,ll,GARK, 	g.dlnv_sigma_beta_G,					g.dLL_lnv)
		d2lnv_gamma_z		=	cf.dd_func_lags(panel,ll,GARK, 	g.dlnv_z_G,							g.dLL_lnv)
		if not self.callback(0.2,'',''):return
		d2lnv_psi_rho		=	cf.dd_func_lags(panel,ll,GARM, 	cf.prod((ll.h_e_val,g.de_rho)),		g.dLL_lnv)
		d2lnv_psi_lambda	=	cf.dd_func_lags(panel,ll,GARM, 	cf.prod((ll.h_e_val,g.de_lambda)),	g.dLL_lnv)
		d2lnv_psi_beta		=	cf.dd_func_lags(panel,ll,GARM, 	cf.prod((ll.h_e_val,g.de_beta)),	g.dLL_lnv)
		d2lnv_psi_z			=	cf.dd_func_lags(panel,ll,GARM, 	ll.h_z_val,								g.dLL_lnv)

		AMAq=(-cf.ARMA_product(ll.AMA_1,q,panel,ll,'q'),ll.AMA_1,q,-1)
		d2lnv_lambda2,		d2e_lambda2		=	cf.dd_func_lags_mult(panel,ll,g,AMAq,	'lambda',	'lambda', transpose=True)
		d2lnv_lambda_rho,	d2e_lambda_rho	=	cf.dd_func_lags_mult(panel,ll,g,AMAq,	'lambda',	'rho' )
		d2lnv_lambda_beta,	d2e_lambda_beta	=	cf.dd_func_lags_mult(panel,ll,g,AMAq,	'lambda',	'beta')

		AMAp=(-cf.ARMA_product(ll.AMA_1,p,panel,ll,'p'),ll.AMA_1,p,-1)
		d2lnv_rho_beta,		d2e_rho_beta	=	cf.dd_func_lags_mult(panel,ll,g,AMAp,	'rho',		'beta', u_gradient=True)
		if not self.callback(0.4,'',''):return
		
		d2lnv_mu_rho,d2lnv_mu_lambda,d2lnv_mu_beta,d2lnv_mu_z,mu=None,None,None,None,None
		if panel.N>1:
			d2lnv_mu_rho			=	cf.sumNT(cf.prod((ll.ddlnvRE_mu_vRE, 	g.dvRE_rho,  	 	g.dLL_lnv)))
			d2lnv_mu_lambda			=	cf.sumNT(cf.prod((ll.ddlnvRE_mu_vRE, 	g.dvRE_lambda,  	g.dLL_lnv)))
			d2lnv_mu_beta			=	cf.sumNT(cf.prod((ll.ddlnvRE_mu_vRE, 	g.dvRE_beta,  	 	g.dLL_lnv)))
			d2lnv_mu_z=None
			d2lnv_mu2=0

		if not self.callback(0.3,'',''):return
		d2lnv_z2				=	cf.dd_func_lags(panel,ll,ll.GAR_1MA, ll.h_2z_val,						g.dLL_lnv) 
		d2lnv_z_rho				=	cf.dd_func_lags(panel,ll,ll.GAR_1MA, cf.prod((ll.h_ez_val,g.de_rho)),	g.dLL_lnv) 
		d2lnv_z_lambda			=	cf.dd_func_lags(panel,ll,ll.GAR_1MA, cf.prod((ll.h_ez_val,g.de_lambda)),g.dLL_lnv) 
		d2lnv_z_beta			=	cf.dd_func_lags(panel,ll,ll.GAR_1MA, cf.prod((ll.h_ez_val,g.de_beta)),	g.dLL_lnv) 
		
		d2lnv_rho2,	d2e_rho2	=	cf.dd_func_lags_mult(panel,ll,g,	None,	'rho',		'rho' )
		d2lnv_beta2,d2e_beta2	=	cf.dd_func_lags_mult(panel,ll,g,	None,	'beta',		'beta')
		


		(de_rho_RE,de_lambda_RE,de_beta_RE)=(g.de_rho_RE,g.de_lambda_RE,g.de_beta_RE)
		(dlnv_sigma_rho,dlnv_sigma_lambda,dlnv_sigma_beta)=(g.dlnv_sigma_rho,g.dlnv_sigma_lambda,g.dlnv_sigma_beta)
		(dlnv_mu,dlnv_z)=(g.dlnv_mu, g.dlnv_z)		

		d2lnv_beta_omega, d2lnv_rho_omega, d2lnv_lambda_omega=None, None, None
			
		if not self.callback(0.6,'',''):return
		#Final:
		D2LL_beta2			=	cf.dd_func(d2LL_de2,	d2LL_dln_de,	d2LL_dln2,	de_beta_RE, 	de_beta_RE,		dlnv_sigma_beta, 	dlnv_sigma_beta,	d2e_beta2, 					d2lnv_beta2)
		D2LL_beta_rho		=	cf.dd_func(d2LL_de2,	d2LL_dln_de,	d2LL_dln2,	de_beta_RE, 	de_rho_RE,		dlnv_sigma_beta, 	dlnv_sigma_rho,		T(d2e_rho_beta), 		T(d2lnv_rho_beta))
		D2LL_beta_lambda	=	cf.dd_func(d2LL_de2,	d2LL_dln_de,	d2LL_dln2,	de_beta_RE, 	de_lambda_RE,	dlnv_sigma_beta, 	dlnv_sigma_lambda,	T(d2e_lambda_beta), 	T(d2lnv_lambda_beta))
		D2LL_beta_gamma		=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_beta_RE, 	None,			dlnv_sigma_beta, 	g.dlnv_gamma,		None, 					T(d2lnv_gamma_beta))
		D2LL_beta_psi		=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_beta_RE, 	None,			dlnv_sigma_beta, 	g.dlnv_psi,			None, 					T(d2lnv_psi_beta))
		D2LL_beta_omega		=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_beta_RE, 	None,			dlnv_sigma_beta, 	g.dlnv_omega,		None, 					d2lnv_beta_omega)
		D2LL_beta_mu		=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_beta_RE, 	None,			dlnv_sigma_beta, 	dlnv_mu,			None, 					d2lnv_mu_beta)
		D2LL_beta_z			=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_beta_RE, 	None,			dlnv_sigma_beta, 	dlnv_z,				None, 					T(d2lnv_z_beta))
		
		D2LL_rho2			=	cf.dd_func(d2LL_de2,	d2LL_dln_de,	d2LL_dln2,	de_rho_RE, 		de_rho_RE,		dlnv_sigma_rho, 	dlnv_sigma_rho,		d2e_rho2, 					d2lnv_rho2)
		D2LL_rho_lambda		=	cf.dd_func(d2LL_de2,	d2LL_dln_de,	d2LL_dln2,	de_rho_RE, 		de_lambda_RE,	dlnv_sigma_rho, 	dlnv_sigma_lambda,	T(d2e_lambda_rho), 		T(d2lnv_lambda_rho))
		D2LL_rho_gamma		=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_rho_RE, 		None,			dlnv_sigma_rho, 	g.dlnv_gamma,		None, 					T(d2lnv_gamma_rho))	
		D2LL_rho_psi		=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_rho_RE, 		None,			dlnv_sigma_rho, 	g.dlnv_psi,			None, 					T(d2lnv_psi_rho))
		D2LL_rho_omega		=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_rho_RE, 		None,			dlnv_sigma_rho, 	g.dlnv_omega,		None, 					d2lnv_rho_omega)
		D2LL_rho_mu			=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_rho_RE, 		None,			dlnv_sigma_rho, 	dlnv_mu,			None, 					T(d2lnv_mu_rho))
		D2LL_rho_z			=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_rho_RE, 		None,			dlnv_sigma_rho, 	dlnv_z,				None, 					T(d2lnv_z_rho))
		
		D2LL_lambda2		=	cf.dd_func(d2LL_de2,	d2LL_dln_de,	d2LL_dln2,	de_lambda_RE, 	de_lambda_RE,	dlnv_sigma_lambda, 	dlnv_sigma_lambda,	T(d2e_lambda2), 		T(d2lnv_lambda2))
		D2LL_lambda_gamma	=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_lambda_RE, 	None,			dlnv_sigma_lambda, 	g.dlnv_gamma,		None, 					T(d2lnv_gamma_lambda))
		D2LL_lambda_psi		=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_lambda_RE, 	None,			dlnv_sigma_lambda, 	g.dlnv_psi,			None, 					T(d2lnv_psi_lambda))
		D2LL_lambda_omega	=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_lambda_RE, 	None,			dlnv_sigma_lambda, 	g.dlnv_omega,		None, 					d2lnv_lambda_omega)
		D2LL_lambda_mu		=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_lambda_RE, 	None,			dlnv_sigma_lambda, 	dlnv_mu,			None, 					T(d2lnv_mu_lambda))
		D2LL_lambda_z		=	cf.dd_func(None,		d2LL_dln_de,	d2LL_dln2,	de_lambda_RE, 	None,			dlnv_sigma_lambda, 	dlnv_z,				None, 					T(d2lnv_z_lambda))
		
		D2LL_gamma2			=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			g.dlnv_gamma, 		g.dlnv_gamma,		None, 					T(d2lnv_gamma2))
		D2LL_gamma_psi		=	cf.dd_func(None,		None,			d2LL_dln2,	None,			None,			g.dlnv_gamma, 		g.dlnv_psi,			None, 					d2lnv_gamma_psi)
		D2LL_gamma_omega	=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			g.dlnv_gamma, 		g.dlnv_omega,		None, 					None)
		D2LL_gamma_mu		=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			g.dlnv_gamma, 		dlnv_mu,			None, 					None)
		D2LL_gamma_z		=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			g.dlnv_gamma, 		dlnv_z,				None, 					d2lnv_gamma_z)
		
		D2LL_psi2			=	cf.dd_func(None,		None,			d2LL_dln2,	None,			None,			g.dlnv_psi, 		g.dlnv_psi,			None, 					None)
		D2LL_psi_omega		=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			g.dlnv_psi, 		g.dlnv_omega,		None, 					None)
		D2LL_psi_mu			=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			g.dlnv_psi, 		dlnv_mu,			None, 					None)
		D2LL_psi_z			=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			g.dlnv_psi, 		dlnv_z,				None, 					d2lnv_psi_z)
		
		D2LL_omega2			=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			g.dlnv_omega, 		g.dlnv_omega,		None, 					None)
		D2LL_omega_mu		=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			g.dlnv_omega, 		g.dlnv_mu,			None, 					None)
		D2LL_omega_z		=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			g.dlnv_omega, 		g.dlnv_z,			None, 					None)
		
		D2LL_mu2			=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			dlnv_mu, 			dlnv_mu,			None, 					None)
		D2LL_mu_z			=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			dlnv_mu, 			dlnv_z,				None, 					d2lnv_mu_z)
		
		D2LL_z2				=	cf.dd_func(None,		None,			d2LL_dln2,	None, 			None,			dlnv_z, 			dlnv_z,				None, 					d2lnv_z2)
		

		
		
		H= [[D2LL_beta2,			D2LL_beta_rho,		D2LL_beta_lambda,		D2LL_beta_gamma,	D2LL_beta_psi,		D2LL_beta_omega,	D2LL_beta_mu,	D2LL_beta_z		],
	        [T(D2LL_beta_rho),		D2LL_rho2,			D2LL_rho_lambda,		D2LL_rho_gamma,		D2LL_rho_psi,		D2LL_rho_omega,		D2LL_rho_mu,	D2LL_rho_z			],
	        [T(D2LL_beta_lambda),	T(D2LL_rho_lambda),	D2LL_lambda2,			D2LL_lambda_gamma,	D2LL_lambda_psi,	D2LL_lambda_omega,	D2LL_lambda_mu,	D2LL_lambda_z		],
	        [T(D2LL_beta_gamma),	T(D2LL_rho_gamma),	T(D2LL_lambda_gamma),	D2LL_gamma2,		D2LL_gamma_psi,		D2LL_gamma_omega, 	D2LL_gamma_mu,	D2LL_gamma_z		],
	        [T(D2LL_beta_psi),		T(D2LL_rho_psi),	T(D2LL_lambda_psi),		T(D2LL_gamma_psi),	D2LL_psi2,			D2LL_psi_omega, 	D2LL_psi_mu,	D2LL_psi_z			],
	        [T(D2LL_beta_omega),	T(D2LL_rho_omega),	T(D2LL_lambda_omega),	T(D2LL_gamma_omega),T(D2LL_psi_omega),	D2LL_omega2, 		D2LL_omega_mu,	D2LL_omega_z		], 
	        [T(D2LL_beta_mu),		T(D2LL_rho_mu),		T(D2LL_lambda_mu),		T(D2LL_gamma_mu),	T(D2LL_psi_mu),		T(D2LL_omega_mu), 	D2LL_mu2,		D2LL_mu_z			],
	        [T(D2LL_beta_z),		T(D2LL_rho_z),		T(D2LL_lambda_z),		T(D2LL_gamma_z),	T(D2LL_psi_z),		T(D2LL_omega_z), 	D2LL_mu_z,		D2LL_z2				]]
		if not self.callback(0.8,'',''):return
		H=cf.concat_matrix(H)
		#for debugging:
		#Hn=debug.hess_debug(ll,panel,g,0.00000001)#debugging
		#v=debug.hess_debug_detail(ll,panel,0.0000001,'grp','beta','beta',0,0)
		#print (time.perf_counter()-tic)
		self.its+=1
		if np.any(np.isnan(H)):
			return None
		#print(H[0]/1e+11)
		return H
	


	
def T(x):
	if x is None:
		return None
	return x.T