import pandas as pd
from pyecharts import Page, Pie, Bar, Line, Gauge, Grid,Overlap
import datetime
import time
import schedule
import os
import re
import pdfkit
from selenium import webdriver
import warnings


# 交易日志分析


class Display:

    def __init__(self):
        self.date = '2020-03-01'
        self.strategies = ['Due2']
        self.path = 'TradeLog'
        self.save_path = 'Report'
        self.pardir = os.path.dirname(__file__)

    def read_data(self, strategy, info_type):
        try:
            df = pd.read_csv(self.path+'\\{0}_{1}_{2}.csv'.format(info_type, strategy, self.date), encoding='GBK')
        except FileNotFoundError:
            raise Exception("please check the path, date, strategies")
        return df

    def plot_pie(self, title, keys, values, title_pos, **kwargs):
        chart = Pie(title, title_pos=title_pos)
        chart.add('', keys, values, is_label_show=True, is_legend_show=True,
                  is_area_show=True, **kwargs)
        # self.page.add(chart)
        chart.render('{}.html'.format(title))
        return chart

    def plot_bar(self, title, keys, values, title_pos, bar_type, **kwargs):
        if bar_type == 'hist':
            chart = Bar(title, 'max:{0[0]} min:{0[1]} std:{0[2]}'.format(kwargs['info']), title_pos=title_pos)
            chart.add('延迟ms', keys, values, bar_category_gap="1%", is_label_show=True, is_legend_show=True,
                      is_area_show=True, is_datazoom_show=False, mark_line=['min', 'max'], mark_point=['average'], **kwargs)
        else:
            chart = Bar(title, title_pos=title_pos)
            chart.add('', keys, values, **kwargs)
            # self.page.add(chart)
        # self.page.add(chart)
        chart.render('{}.html'.format(title))
        return chart

    def plot_line(self, title, keys, values, **kwargs):
        if 'compos' in kwargs.keys() and kwargs['compos'] and 'base_line' in kwargs.keys():
            chart = Overlap('风险敞口和价格',width=1360, height=700)
            base_chart = kwargs['base_line']
            line = Line()
            line.add('', keys, values, **kwargs)
            chart.add(base_chart)
            chart.add(line, yaxis_index=1, is_add_yaxis=True)
            self.page.add(chart)
        else:
            chart = Line(title, title_pos='left')
            chart.add('', keys, values, **kwargs)
            chart.render('{}.html'.format(title))
        return chart

    def create_grid(self, charts: list, option: list):
        grid = Grid(width=1400)
        grid.add(charts[0], grid_right=option[0])
        grid.add(charts[1], grid_left=option[1])
        self.page.add(grid)

    def plot_order(self, strategy):
        order_df = self.read_data(strategy, 'order')
        state_count = order_df.groupby('State', as_index=True)['State'].count()
        state_keys, state_values = list(state_count.index), list(state_count)
        pie1 = self.plot_pie('成交状态', state_keys, state_values, center=[25, 50], title_pos='22%', legend_pos='5%',
                             legend_orient="vertical",)
        side_count = order_df.groupby('Side', as_index=True)['Side'].count()
        side_keys, side_values = list(side_count.index), list(side_count)
        pie2 = self.plot_pie('下单分布', side_keys, side_values, center=[75, 50], title_pos='72%', lengend_pos='80%',
                             legend_orient="vertical",)
        self.create_grid([pie1, pie2], ['50%', '50%'])
        latency_keys, latency_values, latency_max, latency_min, latency_std = Display.get_latency(order_df,
                                                                                                  log_type='order')
        self.order_latency = self.plot_bar('Order-延迟分布', latency_keys, latency_values, title_pos='22%',
                                           bar_type='hist', info=[latency_max, latency_min, latency_std], legend_pos='5%',
                                           xaxis_name='时间ms')

    def plot_trade(self, strategy):
        trade_df = self.read_data(strategy, 'trade')
        latency_keys, latency_values, latency_max, latency_min, latency_std = Display.get_latency(trade_df,
                                                                                                  log_type='trade')
        self.trade_latency = self.plot_bar('Trade-延迟分布', latency_keys, latency_values, title_pos='72%',
                                           bar_type='hist', info=[latency_max, latency_min, latency_std], lengend_pos='80%',
                                           xaxis_name='时间ms')
        self.create_grid([self.order_latency, self.trade_latency], ['55%', '55%'])
        trade_volume = trade_df['Quantity'].sum()
        # TODO:暂时没想好怎么展示单个数字，所以使用了柱状图
        trade_count = trade_df.count()['Quantity']
        trade_chart1 = Bar('Trade-Volume', title_pos='22%')
        trade_chart1.add('', ['Volume'], [trade_volume], is_legend_show=True)
        trade_chart2 = Bar('Trade-Count', title_pos='72%')
        trade_chart2.add('', ['Count'], [trade_count], is_legend_show=True)
        self.create_grid([trade_chart1, trade_chart2],['55%','55%'])
        # TODO:饼状图展示
        # long/short count
        side_count = trade_df.groupby('Side', as_index=True)['Side'].count()
        side_count_keys = list(side_count.index)
        side_count_values = list(side_count)
        side_count_chart = self.plot_bar('Long-Short-Count', side_count_keys, side_count_values, title_pos='22%',
                                         bar_type='normal', yaxis_formatter='笔', xaxis_name='方向')
        # long/short volume
        # TODO：柱状图展示
        side_sum = trade_df.groupby('Side', as_index=True)['Quantity'].sum()
        side_sum_keys = list(side_sum.index)
        side_sum_values = list(side_sum)
        side_volume_chart = self.plot_bar('Long-Short-Volume', side_sum_keys, side_sum_values, title_pos='70%', bar_type='normal')
        self.create_grid([side_count_chart, side_volume_chart],['55%','55%'])

    def plot_performance(self, strategy):
        perform_df = self.read_data(strategy, 'performance')
        perform_df['new_time'] = perform_df['Time'].apply(lambda x: x[2:])
        perform_df['new_time'] = perform_df['time']+perform_df['new_time']
        # TODO:堆积图展示
        exposure = perform_df['Exposure']
        exposure_keys = list(perform_df['new_time'])
        exposure_values = list(exposure)
        exposure_line = self.plot_line('风险敞口和报价', exposure_keys, exposure_values, area_opacity=0.4,
                                       is_datazoom_show=True, compos=True, is_label_show=True, is_splitline_show=False,
                                       yaxis_name='Exposure')
        # TODO:line图展示
        quoter_mid = perform_df['Quoter_Mid']
        quoter_mid_values = list(quoter_mid)
        overlap1 = self.plot_line('报价', exposure_keys, quoter_mid_values, is_datazoom_show=True, yaxis_min='dataMin',
                                   base_line=exposure_line, compos=True, is_legend_show=True, is_splitline_show=False,
                                   yaxis_name='Quoter_Mid', yaxis_name_gap='40')
        # TODO:堆积图展示
        exposure_line2 = self.plot_line('Exposure And PnL_Total', exposure_keys, exposure_values, area_opacity=0.4,
                                        is_datazoom_show=True, compos=True, is_label_show=True, is_splitline_show=False,
                                        yaxis_name='Exposure')
        pnl_total = list(perform_df['PnL_Total'])
        overlap2 = self.plot_line('PnL_Total', exposure_keys, pnl_total, is_datazoom_show=True, base_line=exposure_line2,
                                   compos=True, is_splitline_show=False, area_opacity=0.4, yaxis_name='PnL_Total')

        quoter_line = self.plot_line('Pnl_Total And Quoter_Mid', exposure_keys, quoter_mid_values, yaxis_min='dataMin',
                                     is_datazoom_show=True, is_label_show=True, is_splitline_show=False,
                                     yaxis_name='Quoter_Mid', yaxis_name_gap='40')
        self.plot_line('PnL_Total', exposure_keys, pnl_total, is_datazoom_show=True, base_line=quoter_line,
                       compos=True, is_splitline_show=False, area_opacity=0.4, yaxis_name='PnL_Total')

    def plot_page(self, strategy):
        self.page = Page('{}-策略交易日志分析'.format(strategy))
        self.plot_performance(strategy)
        self.plot_order(strategy)
        self.plot_trade(strategy)
        self._check_path_()
        file_name = self.save_path+'\\{0}-策略交易日志分析{1}.html'.format(strategy, self.date.replace('-', ''))
        self.page.render(file_name)
        self.trans_html_to_img(file_name=file_name, out_name=file_name.split('.')[0]+'.png')
        # pass

    def _check_path_(self):
        if os.path.exists(self.save_path):
            pass
        else:
            os.mkdir(self.save_path)

    # TODO:html转pdf，本机出错，或许linux会表现好
    @staticmethod
    def trans_html_to_pdf(file_name, out_name):
        config = pdfkit.configuration(wkhtmltopdf='D:\\tools\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
        pdfkit.from_file(file_name, out_name, configuration=config)

    # html 转 img
    def trans_html_to_img(self, file_name, out_name):
        option = webdriver.ChromeOptions()
        option.add_argument('--headless')
        option.add_argument('--disable-gpu')
        option.add_argument("--window-size=1280,1024")
        option.add_argument("--hide-scrollbars")

        driver = webdriver.Chrome(chrome_options=option)

        driver.get('file:///'+self.pardir+'/'+file_name)
        time.sleep(1)
        scroll_width = driver.execute_script('return document.body.parentNode.scrollWidth')
        scroll_height = driver.execute_script('return document.body.parentNode.scrollHeight')
        driver.set_window_size(scroll_width, scroll_height)
        driver.save_screenshot(out_name)
        driver.quit()

    @staticmethod
    def check_time_format(data, time_columns):
        time_df = data[time_columns]
        time_df = time_df.apply(lambda x: x.str.len(), axis=0)
        drop_index = time_df[time_df != 7].dropna(how='all').index
        data = data.drop(drop_index, axis=0)
        return data

    @staticmethod
    def trans_datetime(_time):
        format_ = '%M:%S.%f'
        return datetime.datetime.strptime(_time, format_)

    @staticmethod
    def get_latency(data, log_type):
        df = data.copy()
        if log_type == 'order':
            try:
                df['new1'] = df['ReceivedTime'].apply(lambda x: Display.trans_datetime(x))
            except:
                df = Display.check_time_format(df, ['ReceivedTime', 'SubmittedTime'])
            df['new1'] = df['ReceivedTime'].apply(lambda x: Display.trans_datetime(x))
            df['new2'] = df['SubmittedTime'].apply(lambda x: Display.trans_datetime(x))
        else:
            try:
                df['new1'] = df['ReceivedTime'].apply(lambda x: Display.trans_datetime(x))
                df['new2'] = df['ExchangeTime'].apply(lambda x: Display.trans_datetime(x))
            except:
                df = Display.check_time_format(df, ['ReceivedTime', 'ExchangeTime'])
            df['new1'] = df['ReceivedTime'].apply(lambda x: Display.trans_datetime(x))
            df['new2'] = df['ExchangeTime'].apply(lambda x: Display.trans_datetime(x))
        df['Latency'] = (df['new1'] - df['new2']).apply(
            lambda x: x.microseconds) / 1000
        df['sid'] = pd.cut(df['Latency'], 10)
        latency_count = df.groupby('sid', as_index=True)['sid'].count()
        latency_std = df['Latency'].std()
        latency_max, latency_min = df['Latency'].max(), df['Latency'].min()
        latency_keys = list(latency_count.index)
        latency_values = list(latency_count)
        latency_keys = [str(k) for k in latency_keys]
        return latency_keys, latency_values, latency_max, latency_min, latency_std

    def main(self):
        for s in self.strategies:
            self.plot_page(s)


def job():
    print('Start Display TradeLog')
    return Display().main()


def exec_regular(time_):
    # 在这里设置执行任务
    schedule.every().day.at(time_).do(job)
    while True:
        schedule.run_pending()
        time.sleep(5)


if __name__ == '__main__':
    Display().main()




    
