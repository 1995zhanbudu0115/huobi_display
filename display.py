import pandas as pd
from pyecharts import Page,Pie,Bar,Line,Gauge
import datetime
import time


class Display:

    def __init__(self):
        # self.date = datetime.date.today()
        self.date = '2020-02-28'
        self.strategys = ['Due2_Lv1']
        self.path = 'TradeLog'

    def read_data(self, strategy, info_type):
        df = pd.read_csv(self.path+'\\{0}_{1}_{2}.csv'.format(info_type, strategy, self.date), encoding='GBK')
        return df

    def plot_pie(self, title, keys, values, **kwargs):
        chart = Pie(title, width=800, title_pos='left')
        chart.add('', keys, values, center=[40, 50], redius=[50, 50], is_label_show=True, is_legend_show=False,
                  is_area_show=True, **kwargs)
        self.page.add(chart)
        chart.render('{}.html'.format(title))

    def plot_bar(self, title, keys, values, info):
        chart = Bar(title, 'max:{0[0]} min:{0[1]} std:{0[2]}'.format(info), width=800, title_pos='left')
        chart.add('延迟ms', keys, values, bar_category_gap="1%", is_label_show=True, is_legend_show=True,
                  is_area_show=True, is_datazoom_show=True,mark_line=['min','max'],mark_point=['average'])
        self.page.add(chart)
        chart.render('{}.html'.format(title))

    def plot_line(self):
        pass

    def plot_order(self, strategy):
        order_df = self.read_data(strategy, 'order')
        state_count = order_df.groupby('State', as_index=True)['State'].count()
        state_keys,state_values= list(state_count.index), list(state_count)
        self.plot_pie('成交状态', state_keys, state_values, color='#c23531')
        side_count = order_df.groupby('Side', as_index=True)['Side'].count()
        side_keys, side_values = list(side_count.index), list(side_count)
        self.plot_pie('下单分布', side_keys, side_values)
        try:
            order_df['new_received'] = order_df['ReceivedTime'].apply(lambda x: Display.trans_datetime(x))
        except:
            order_df = Display.check_time_format(order_df, ['ReceivedTime', 'SubmittedTime'])
        order_df['new_received'] = order_df['ReceivedTime'].apply(lambda x: Display.trans_datetime(x))
        order_df['new_submitted'] = order_df['SubmittedTime'].apply(lambda x: Display.trans_datetime(x))
        order_df['Latency'] = (order_df['new_received'] - order_df['new_submitted']).apply(
            lambda x: x.microseconds) / 1000
        order_df['sid'] = pd.cut(order_df['Latency'], 10)
        latency_count = order_df.groupby('sid', as_index=True)['sid'].count()
        latency_std = order_df['Latency'].std()
        latency_max, latency_min = order_df['Latency'].max(), order_df['Latency'].min()
        latency_keys = list(latency_count.index)
        latency_values = list(latency_count)
        latency_keys = [str(k) for k in latency_keys]
        self.plot_bar('Order-延迟分布', latency_keys, latency_values,[latency_max,latency_min, latency_std])

    def plot_trade(self, strategy):
        trade_df = self.read_data(strategy, 'trade')
        pass

    def plot_performance(self):
        pass

    def plot_page(self, strategy):
        self.page = Page('{}-策略交易日志分析'.format(strategy))
        # self.plot_order(strategy)
        self.plot_trade(strategy)
        # self.plot_performance(strategy)
        # pass

    def _check_path_(self):
        pass

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

    def main(self):
        for s in self.strategys:
            self.plot_page(s)


if __name__ == '__main__':
    Display().main()